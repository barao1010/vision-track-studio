"""GPL-2.0-or-later. Predictable, bounded digital camera framing for static sources.

The operator selects a person using the existing identity association logic.
This module only computes a normalized crop; the OBS frontend performs the
actual scene transform. No physical PTZ commands are sent in fixed mode.
"""
import math

def clamp(value, lower, upper):
    return min(upper, max(lower, value))


class DigitalZoomController:
    def __init__(self, max_zoom=2.7, subject_height=.52, smoothing=.20):
        self.max_zoom = max(1., float(max_zoom))
        self.subject_height = clamp(float(subject_height), .3, .8)
        self.smoothing = clamp(float(smoothing), .03, .9)
        self.reset()

    def reset(self):
        self.center_x = .5
        self.center_y = .5
        self.zoom = 1.
        self.locked = False

    def update(self, width, height, box, velocity=(0, 0)):
        if width <= 0 or height <= 0 or len(box) != 4:
            return None
        x, y, bw, bh = box
        if not all(math.isfinite(float(v)) for v in box) or bw <= 0 or bh <= 0:
            return None
        normalized_height = bh / height
        target_zoom = clamp(self.subject_height / normalized_height, 1., self.max_zoom)
        # Leave headroom and avoid an unnatural face-only close-up.
        view_h = 1. / target_zoom
        cx = clamp((x + bw * .5) / width + clamp(velocity[0], -.8, .8) * .03,
                   .5 / target_zoom, 1. - .5 / target_zoom)
        cy = clamp(y / height + view_h * .36, .5 * view_h, 1. - .5 * view_h)
        blend = 1. if not self.locked else self.smoothing
        self.zoom += (target_zoom - self.zoom) * blend
        crop_w = 1. / self.zoom
        crop_h = crop_w
        self.center_x = clamp(self.center_x + (cx - self.center_x) * blend, crop_w / 2, 1. - crop_w / 2)
        self.center_y = clamp(self.center_y + (cy - self.center_y) * blend, crop_h / 2, 1. - crop_h / 2)
        self.locked = True
        left = self.center_x - crop_w / 2
        top = self.center_y - crop_h / 2
        return {"left": round(left, 6), "top": round(top, 6),
                "width": round(crop_w, 6), "height": round(crop_h, 6),
                "zoom": round(self.zoom, 4)}
