"""Vision Track Studio - reusable person tracking / PTZ controller core.

No camera or OBS integration is implied. A vision detector must provide the
selected person's bounding box on each frame; a PTZ driver implements PTZOutput.
Safety: no movement until an explicit selection; stop on target loss.
"""
from dataclasses import dataclass
from typing import Protocol, Optional
import time
import math

@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float
    def center(self):
        return (self.x + self.w / 2, self.y + self.h / 2)

class PTZOutput(Protocol):
    def move(self, pan: float, tilt: float, zoom: float) -> None: ...
    def stop(self) -> None: ...

class TargetPTZController:
    def __init__(self, output: PTZOutput, deadzone=0.075, gain=0.7,
                 max_speed=0.5, smoothing=0.20, lost_after=0.8, min_interval=0.10):
        self.output = output
        self.deadzone = deadzone
        self.gain = gain
        self.max_speed = max_speed
        self.smoothing = smoothing
        self.lost_after = lost_after
        self.min_interval = min_interval
        self.selected_id: Optional[int] = None
        self.last_seen: Optional[float] = None
        self.last_sent = -float('inf')
        self.previous = (0.0, 0.0)
        self.running = False
        self.last_active = False

    def select(self, target_id: int):
        self.stop()
        self.selected_id = target_id
        self.running = True

    def stop(self):
        self.output.stop()
        self.running = False
        self.last_sent = -float('inf')
        self.selected_id = None
        self.last_seen = None
        self.last_active = False
        self.previous = (0.0, 0.0)

    def _axis(self, error: float):
        if abs(error) <= self.deadzone:
            return 0.0
        speed = self.gain * error
        return max(-self.max_speed, min(self.max_speed, speed))

    def update(self, frame_w: int, frame_h: int, detections: dict[int, Box], now=None):
        now = time.monotonic() if now is None else now
        if not self.running or self.selected_id is None:
            return
        if frame_w <= 0 or frame_h <= 0:
            raise ValueError("Frame size must be positive")
        box = detections.get(self.selected_id)
        if box is None:
            if self.last_seen is not None and now - self.last_seen >= self.lost_after and self.last_active:
                self.output.stop()
                self.last_active = False
                self.previous = (0.0, 0.0)
                self.last_sent = -float('inf')
            return
        if not all(math.isfinite(value) for value in (box.x, box.y, box.w, box.h)) or box.w <= 0 or box.h <= 0:
            if self.last_active:
                self.output.stop()
                self.last_active = False
            self.previous = (0.0, 0.0)
            self.last_sent = -float('inf')
            return
        self.last_seen = now
        cx, cy = box.center()
        pan_error = (cx / frame_w - 0.5) * 2
        tilt_error = (cy / frame_h - 0.5) * 2
        desired = (self._axis(pan_error), self._axis(tilt_error))
        if desired == (0.0, 0.0):
            if self.last_active:
                self.output.stop()
            self.last_active = False
            self.previous = (0.0, 0.0)
            self.last_sent = -float('inf')
            return
        pan = (1 - self.smoothing) * self.previous[0] + self.smoothing * desired[0]
        tilt = (1 - self.smoothing) * self.previous[1] + self.smoothing * desired[1]
        if now - self.last_sent >= self.min_interval:
            # Zoom is deliberately zero until calibrated for the camera model.
            self.output.move(pan, tilt, 0.0)
            self.previous = (pan, tilt)
            self.last_sent = now
            self.last_active = True

