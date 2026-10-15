"""Original target-state and digital framing algorithms, independent of detectors.

Coordinates are normalized 0..1. Integrate a detector separately; these algorithms
are not evidence of successful camera tracking.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Detection:
    box: tuple[float, float, float, float]
    signature: tuple[float, ...]
    confidence: float = 1.0


def similarity(a, b):
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a) * sum(x * x for x in b))
    return dot / norm if norm else 0.0


class TargetLock:
    """Explicit selection; uncertainty suspends motion; reference appearance stays fixed."""
    def __init__(self, confirmations=3, threshold=.85, margin=.12):
        self.confirmations = confirmations
        self.threshold = threshold
        self.margin = margin
        self.reference = None
        self.pending = None
        self.streak = 0
        self.state = 'unselected'
        self.target = None
        self.recovery_required = confirmations

    def select(self, detection):
        if not detection.signature or not all(math.isfinite(value) for value in detection.signature) or sum(value * value for value in detection.signature) < 1e-12:
            raise ValueError('Seleção sem assinatura')
        self.reference = detection.signature
        self.target = detection
        self.state = 'locked'
        self.streak = 0
        self.pending = None
        self.recovery_required = self.confirmations

    def update(self, detections):
        if self.reference is None:
            return None
        ranked = sorted(((similarity(self.reference, d.signature), d) for d in detections), key=lambda item: item[0], reverse=True)
        uncertain = not ranked or ranked[0][0] < self.threshold or (len(ranked) > 1 and ranked[0][0] - ranked[1][0] < self.margin)
        if uncertain:
            ambiguous = len(ranked) > 1
            self.state = 'ambiguous' if ambiguous else 'lost'
            if ambiguous:
                self.recovery_required = max(self.confirmations, 5)
            self.target = self.pending = None
            self.streak = 0
            return None
        candidate = ranked[0][1]
        if self.state == 'locked' and self.target is not None:
            previous = self.target.box
            current = candidate.box
            distance = math.hypot(current[0] + current[2] / 2 - previous[0] - previous[2] / 2, current[1] + current[3] / 2 - previous[1] - previous[3] / 2)
            area_ratio = (current[2] * current[3]) / max(1e-9, previous[2] * previous[3])
            if distance > .18 or not .35 <= area_ratio <= 2.8:
                self.state = 'lost'
                self.target = None
                self.streak = 0
        if self.state != 'locked':
            # Spatial continuity across recovery frames prevents combining different people.
            if self.pending:
                distance = sum((candidate.box[i] - self.pending.box[i]) ** 2 for i in (0, 1))
                if distance > .04:
                    self.streak = 0
            self.pending = candidate
            self.streak += 1
            if self.streak < self.recovery_required:
                self.state = 'recovering'
                return None
        self.state, self.target = 'locked', candidate
        self.recovery_required = self.confirmations
        self.pending = None
        self.streak = 0
        return candidate


PROFILES = {'Cinema': (.7, .08), 'Suave': (1.4, .05), 'Dinâmico': (3.0, .03)}


class DigitalFramer:
    """Time-based crop smoothing with bounded speed and a central deadband."""
    def __init__(self, profile='Cinema'):
        self.profile = profile
        self.center = (.5, .5)

    def update(self, box, dt, zoom=2.0):
        if self.profile not in PROFILES or not math.isfinite(dt) or not math.isfinite(zoom) or not 1 <= zoom <= 8:
            raise ValueError('Parâmetros de enquadramento inválidos')
        gain, deadband = PROFILES[self.profile]
        half = .5 / zoom
        if box is not None:
            target = (box[0] + box[2] / 2, box[1] + box[3] / 2)
            amount = 1 - math.exp(-gain * min(max(dt, 0), .25))
            self.center = tuple(old + max(-.1, min(.1, (new - old) * amount)) if abs(new - old) > deadband else old for old, new in zip(self.center, target))
        self.center = tuple(max(half, min(1 - half, value)) for value in self.center)
        return (self.center[0] - half, self.center[1] - half, 2 * half, 2 * half)

    def render(self, frame, box, dt, zoom=2.0):
        x, y, width, height = self.update(box, dt, zoom)
        crop = (round(x * frame.width), round(y * frame.height), round((x + width) * frame.width), round((y + height) * frame.height))
        return frame.crop(crop).resize(frame.size)
