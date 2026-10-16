// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <obs.h>
#include <QString>
#include <algorithm>
#include <cmath>
#include <vector>

class FixedCameraSceneZoom {
    struct Saved {
        obs_sceneitem_t *item = nullptr;
        obs_transform_info info{};
        obs_sceneitem_crop crop{};
    };
    OBSBasic *studio = nullptr;
    std::vector<Saved> saved;
    QString sourceName;

    static void reset(Saved &state) {
        obs_sceneitem_set_crop(state.item, &state.crop);
        obs_sceneitem_set_info2(state.item, &state.info);
        obs_sceneitem_release(state.item);
    }

    static bool applyTo(Saved &state, double left, double top, double width, double height) {
        obs_source_t *source = obs_sceneitem_get_source(state.item);
        const int sourceWidth = static_cast<int>(obs_source_get_width(source));
        const int sourceHeight = static_cast<int>(obs_source_get_height(source));
        const int originalWidth = sourceWidth-state.crop.left-state.crop.right;
        const int originalHeight = sourceHeight-state.crop.top-state.crop.bottom;
        if (sourceWidth<=0 || sourceHeight<=0 || originalWidth<=0 || originalHeight<=0) return false;
        obs_sceneitem_crop crop{
            static_cast<int>(std::round(left*sourceWidth)),
            static_cast<int>(std::round(top*sourceHeight)),
            static_cast<int>(std::round((1-left-width)*sourceWidth)),
            static_cast<int>(std::round((1-top-height)*sourceHeight))};
        const int effectiveWidth=sourceWidth-crop.left-crop.right;
        const int effectiveHeight=sourceHeight-crop.top-crop.bottom;
        if (effectiveWidth<16 || effectiveHeight<16) return false;
        obs_transform_info transform=state.info;
        transform.scale.x *= static_cast<float>(originalWidth)/effectiveWidth;
        transform.scale.y *= static_cast<float>(originalHeight)/effectiveHeight;
        obs_sceneitem_set_crop(state.item,&crop);
        obs_sceneitem_set_info2(state.item,&transform);
        return true;
    }

public:
    explicit FixedCameraSceneZoom(OBSBasic *main) : studio(main) {}
    ~FixedCameraSceneZoom() { restore(); }
    void setSource(const QString &name) {
        if (sourceName==name) return;
        restore();
        sourceName=name;
    }
    void restore() {
        for (auto &state:saved) reset(state);
        saved.clear();
    }
    bool apply(double left,double top,double width,double height) {
        if (!studio || sourceName.isEmpty() || !std::isfinite(left) || !std::isfinite(top) ||
            !std::isfinite(width) || !std::isfinite(height) || left<0 || top<0 || width<=.01 || height<=.01 ||
            left+width>1.00001 || top+height>1.00001) return false;
        const QByteArray name=sourceName.toUtf8();
        std::vector<obs_sceneitem_t *> targets;
        auto addScene=[&](obs_scene_t *scene) {
            auto *item=scene ? obs_scene_find_source_recursive(scene,name.constData()) : nullptr;
            if (item && std::find(targets.begin(),targets.end(),item)==targets.end()) targets.push_back(item);
        };
        OBSScene preview=studio->GetCurrentScene();
        addScene(preview);
        if (studio->IsPreviewProgramMode()) {
            OBSSource program=studio->GetProgramSource();
            addScene(program ? obs_scene_from_source(program) : nullptr);
        }
        // Key snapshots by scene item, not by preview/program role. A studio
        // transition may swap those roles; each original must be captured once.
        for (auto it=saved.begin();it!=saved.end();) {
            if (std::find(targets.begin(),targets.end(),it->item)==targets.end()) {
                reset(*it);
                it=saved.erase(it);
            } else ++it;
        }
        bool applied=false;
        for (auto *item:targets) {
            auto it=std::find_if(saved.begin(),saved.end(),[item](const Saved &s) { return s.item==item; });
            if (it==saved.end()) {
                Saved state;
                state.item=item;
                obs_sceneitem_addref(item);
                obs_sceneitem_get_crop(item,&state.crop);
                obs_sceneitem_get_info2(item,&state.info);
                saved.push_back(state);
                it=saved.end()-1;
            }
            applied=applyTo(*it,left,top,width,height) || applied;
        }
        return applied;
    }
};
