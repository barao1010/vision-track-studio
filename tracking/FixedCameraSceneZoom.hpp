// SPDX-License-Identifier: GPL-2.0-or-later
// Vision Track Studio, 2026-10-14: temporary OBS scene framing for fixed cameras.
// This is deliberately independent from the OBS Settings UI.
#pragma once
#include <obs.h>
#include <QString>
#include <algorithm>
#include <cmath>

class FixedCameraSceneZoom {
    OBSBasic *studio = nullptr;  // Parent window outlives its dock.
    obs_sceneitem_t *edited = nullptr; // Explicit retained reference.
    obs_transform_info originalInfo{};
    obs_sceneitem_crop originalCrop{};
    QString sourceName;

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
        if (!edited)
            return;
        obs_sceneitem_set_crop(edited, &originalCrop);
        obs_sceneitem_set_info2(edited, &originalInfo);
        obs_sceneitem_release(edited);
        edited = nullptr;
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
        // Zoom is only applied to a source explicitly chosen by the operator
        // and currently present in the active OBS scene.
        OBSScene scene = studio->GetCurrentScene();
        if (!scene) {
            restore();
            return false;
        }
        const QByteArray selected = sourceName.toUtf8();
        obs_sceneitem_t *item = obs_scene_find_source(scene, selected.constData());
        if (!item) {
            restore();
            return false;
        }
        if (edited != item) {
            restore();
            obs_sceneitem_addref(item);
            edited = item;
            obs_sceneitem_get_info2(item, &originalInfo);
            obs_sceneitem_get_crop(item, &originalCrop);
        }
        obs_source_t *source = obs_sceneitem_get_source(item);
        const auto sourceWidth = obs_source_get_width(source);
        const auto sourceHeight = obs_source_get_height(source);
        if (sourceWidth == 0 || sourceHeight == 0)
            return false;
        // All crops are fractions of the original, not the already-cropped
        // dimensions. This avoids accumulating rounding drift over time.
        obs_sceneitem_crop crop = {
            static_cast<int>(std::round(left * sourceWidth)),
            static_cast<int>(std::round(top * sourceHeight)),
            static_cast<int>(std::round((1 - left - width) * sourceWidth)),
            static_cast<int>(std::round((1 - top - height) * sourceHeight))
        };
        const int effectiveWidth = static_cast<int>(sourceWidth) - crop.left - crop.right;
        const int effectiveHeight = static_cast<int>(sourceHeight) - crop.top - crop.bottom;
        if (effectiveWidth < 16 || effectiveHeight < 16)
            return false;
        obs_transform_info framed = originalInfo;
        // Preserve the scene item's pre-existing footprint, anchor and position.
        framed.scale.x *= static_cast<float>(sourceWidth) / effectiveWidth;
        framed.scale.y *= static_cast<float>(sourceHeight) / effectiveHeight;
        obs_sceneitem_set_crop(item, &crop);
        obs_sceneitem_set_info2(item, &framed);
        return true;
    }
};
