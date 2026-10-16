// SPDX-License-Identifier: GPL-2.0-or-later
// Vision Track Studio, 2026-10-14: reversible fixed-camera framing
// for OBS preview and, when distinct, the live Studio Mode program.
#pragma once
#include <obs.h>
#include <QString>
#include <algorithm>
#include <cmath>

class FixedCameraSceneZoom {
    struct Saved {
        obs_sceneitem_t *item = nullptr;
        obs_transform_info info{};
        obs_sceneitem_crop crop{};
    };
    OBSBasic *studio = nullptr;
    Saved preview;
    Saved program;
    QString sourceName;

    static void reset(Saved &state)
    {
        if (!state.item)
            return;
        obs_sceneitem_set_crop(state.item, &state.crop);
        obs_sceneitem_set_info2(state.item, &state.info);
        obs_sceneitem_release(state.item);
        state.item = nullptr;
    }

    bool applyTo(Saved &state, obs_scene_t *scene, double left, double top,
                 double width, double height, obs_sceneitem_t *exclude = nullptr)
    {
        if (!scene) {
            reset(state);
            return false;
        }
        const QByteArray utf8 = sourceName.toUtf8();
        obs_sceneitem_t *item = obs_scene_find_source_recursive(scene, utf8.constData());
        if (!item || item == exclude) {
            reset(state);
            return false;
        }
        if (state.item != item) {
            reset(state);
            obs_sceneitem_addref(item);
            state.item = item;
            obs_sceneitem_get_crop(item, &state.crop);
            obs_sceneitem_get_info2(item, &state.info);
        }
        obs_source_t *source = obs_sceneitem_get_source(item);
        const auto sourceWidth = obs_source_get_width(source);
        const auto sourceHeight = obs_source_get_height(source);
        if (sourceWidth == 0 || sourceHeight == 0)
            return false;
        // Coordinates are normalized against the input signal.
        obs_sceneitem_crop crop {
            static_cast<int>(std::round(left * sourceWidth)),
            static_cast<int>(std::round(top * sourceHeight)),
            static_cast<int>(std::round((1 - left - width) * sourceWidth)),
            static_cast<int>(std::round((1 - top - height) * sourceHeight))
        };
        const int effectiveWidth = static_cast<int>(sourceWidth) - crop.left - crop.right;
        const int effectiveHeight = static_cast<int>(sourceHeight) - crop.top - crop.bottom;
        if (effectiveWidth < 16 || effectiveHeight < 16)
            return false;
        obs_transform_info transform = state.info;
        // Keep the source in its original OBS footprint while digitally
        // reframing its content. Restore exactly on stop/disconnect.
        transform.scale.x *= static_cast<float>(sourceWidth - state.crop.left - state.crop.right) / effectiveWidth;
        transform.scale.y *= static_cast<float>(sourceHeight - state.crop.top - state.crop.bottom) / effectiveHeight;
        obs_sceneitem_set_crop(item, &crop);
        obs_sceneitem_set_info2(item, &transform);
        return true;
    }

public:
    explicit FixedCameraSceneZoom(OBSBasic *main) : studio(main) {}
    ~FixedCameraSceneZoom() { restore(); }

    void setSource(const QString &name)
    {
        if (sourceName == name)
            return;
        restore();
        sourceName = name;
    }

    void restore()
    {
        // Both records retain a reference so that scene transitions cannot
        // leave a modified scene item behind after a mode change.
        reset(preview);
        reset(program);
    }

    bool apply(double left, double top, double width, double height)
    {
        if (!studio || sourceName.isEmpty())
            return false;
        if (!std::isfinite(left) || !std::isfinite(top) ||
            !std::isfinite(width) || !std::isfinite(height))
            return false;
        if (left < 0 || top < 0 || width <= .01 || height <= .01 ||
            left + width > 1.00001 || top + height > 1.00001)
            return false;
        OBSScene current = studio->GetCurrentScene();
        const bool previewOk = applyTo(preview, current, left, top, width, height);
        if (studio->IsPreviewProgramMode()) {
            OBSSource liveSource = studio->GetProgramSource();
            obs_scene_t *liveScene = liveSource ? obs_scene_from_source(liveSource) : nullptr;
            const bool programOk = applyTo(program, liveScene, left, top, width, height, preview.item);
            return previewOk || programOk;
        }
        reset(program);
        return previewOk;
    }
};
