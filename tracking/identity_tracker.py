"""GPL-2.0-or-later. Port of Vision Track AI's operator-locked association policy.
Appearance is a session-only upper-body colour sample, never a named identity.
"""
import math
from association import overlap


def similarity(a, b):
    if a is None or b is None or len(a) != len(b) or len(a) < 3:
        return 0
    if not all(math.isfinite(float(v)) for v in list(a) + list(b)):
        return 0
    return max(0, 1 - 1.55 * math.sqrt(sum((max(0, min(1, float(x))) - max(0, min(1, float(y)))) ** 2 for x, y in zip(a, b)) / len(a)))


def center(box):
    x, y, w, h = box
    return x + w / 2, y + h / 2


class IdentityTracker:
    def __init__(self):
        self.clear()

    def clear(self):
        self.box = self.signature = None
        self.state = 'idle'
        self.crossing = []
        self.strict = False
        self.pending = None
        self.last_frame = None
        self.velocity = (0., 0.)
        self.last_time = None

    def select(self, box, signature, now):
        self.clear()
        self.box, self.signature = tuple(box), tuple(signature)
        self.state = 'locked'
        self.last_time = now

    def update(self, detections, signatures, now, frame_id):
        if self.box is None or frame_id == self.last_frame:
            return None
        self.last_frame = frame_id
        dt = max(.035, min(.5, now - (self.last_time or now)))
        cx, cy = center(self.box)
        h = max(self.box[3], 1)
        candidates = []
        for box, sig in zip(detections, signatures):
            app = similarity(self.signature, sig)
            bx, by = center(box)
            dist = math.hypot(bx - cx, by - cy) / h
            ratio = min(h, box[3]) / max(h, box[3], 1)
            gate = 1.82 if self.strict else .97
            if app < (.955 if self.strict else .78) or dist > gate or ratio < .57:
                continue
            score = .32 * max(0, 1 - dist / gate) + .22 * overlap(self.box, box) + .38 * app + .08 * ratio
            candidates.append((score, app, tuple(box), tuple(sig)))
        candidates.sort(key=lambda c: c[0], reverse=True)
        if not candidates:
            return self.hold('ambiguous' if self.strict else 'lost')
        best = candidates[0]
        if self.strict and (best[1] < .965 or (len(candidates) > 1 and best[1] - candidates[1][1] < .12) or any(similarity(s, best[3]) >= .955 for s in self.crossing)):
            return self.hold('ambiguous')
        ambiguous = any(abs(best[1] - c[1]) < .12 and (abs(best[0] - c[0]) < .12 or math.dist(center(best[2]), center(c[2])) < h * .52) for c in candidates[1:])
        if ambiguous:
            self.crossing = [c[3] for c in candidates[1:5]]
            self.strict = True
            return self.hold('ambiguous')
        if self.state != 'locked':
            count = self.pending[1] + 1 if self.pending and math.dist(center(self.pending[0]), center(best[2])) < h * .32 else 1
            self.pending = (best[2], count)
            self.state = 'recovering'
            if count < (5 if self.strict else 3):
                return None
        oldcx, oldcy = center(self.box)
        ncx, ncy = center(best[2])
        vx = max(-.8, min(.8, (self.velocity[0] + .14 * (ncx-oldcx) / h / dt) * .85))
        vy = max(-.8, min(.8, (self.velocity[1] + .14 * (ncy-oldcy) / h / dt) * .85))
        w = self.box[2] + .22 * (best[2][2] - self.box[2])
        nh = self.box[3] + .22 * (best[2][3] - self.box[3])
        ncx, ncy = oldcx + .48 * (ncx-oldcx), oldcy + .48 * (ncy-oldcy)
        self.box = (ncx-w/2, ncy-nh/2, w, nh)
        self.velocity = (vx, vy)
        self.last_time = now
        self.state = 'locked'
        self.strict = False
        self.crossing = []
        self.pending = None
        return self.box

    def hold(self, state):
        self.state = state
        self.pending = None
        self.velocity = (0., 0.)
        return None
