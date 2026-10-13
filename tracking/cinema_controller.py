"""GPL-2.0-or-later. Physical PTZ motion settings from Vision Track AI cinema.js."""
import math

PRESETS = {
    'cinema': dict(dead=.07, deadY=.06, maxPan=.32, accel=.55, gain=1.5, lookAhead=.1, cooldown=.6),
    'suave': dict(dead=.1, deadY=.08, maxPan=.22, accel=.32, gain=1.1, lookAhead=.08, cooldown=1.),
    'dinamico': dict(dead=.05, deadY=.05, maxPan=.6, accel=1.2, gain=2.3, lookAhead=.12, cooldown=.3),
}

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

class CinemaPTZController:
    def __init__(self, output, preset='cinema', max_speed=.5):
        self.output = output
        self.preset = PRESETS.get(preset, PRESETS['cinema'])
        self.limit = max_speed
        self.reset()

    def reset(self):
        self.v = [0., 0.]
        self.moving = [False, False]
        self.speed = self.cool = 0.
        self.last = None
        self.active = False

    def stop(self):
        self.output.stop()
        self.reset()

    def update(self, width, height, box, velocity, now):
        if not all(math.isfinite(v) for v in box) or width <= 0 or height <= 0 or box[2] <= 0 or box[3] <= 0:
            self.stop()
            return
        p = self.preset
        dt = clamp(now - self.last, .01, .5) if self.last is not None else .1
        self.last = now
        vx = velocity[0] * box[3] / width
        self.speed += (abs(vx) - self.speed) * min(1, dt * 2.2)
        motion_stopped = self.speed < .012
        direction = (1 if vx > 0 else -1 if vx < 0 else 0) * min(1, self.speed / .12)
        errors = [(box[0] + box[2]/2)/width - (.5 - p['lookAhead']*direction), box[1]/height - .12]
        dead = [p['dead'], p['deadY']]
        self.cool = max(0, self.cool-dt)
        for i in range(2):
            if not self.moving[i] and abs(errors[i]) > dead[i] and self.cool == 0:
                self.moving[i] = True
            if self.moving[i] and abs(errors[i]) < dead[i]*.35 and (i == 1 or motion_stopped):
                self.moving[i] = False
                if i == 0:
                    self.cool = p['cooldown']
        factor = clamp(self.speed/.1, 0, 1.8)
        maxv = p['maxPan']*(.3+factor)
        accel = p['accel']*(.45+factor*.8)
        targets = [clamp(p['gain']*errors[0] + vx*.85, -maxv, maxv) if self.moving[0] else 0,
                   clamp(p['gain']*.6*errors[1], -maxv*.5, maxv*.5) if self.moving[1] else 0]
        for i in range(2):
            self.v[i] += clamp(targets[i]-self.v[i], -accel*dt*(.6 if i else 1), accel*dt*(.6 if i else 1))
        pan, tilt = clamp(self.v[0]/.6, -self.limit, self.limit), clamp(self.v[1]/.4, -self.limit, self.limit)
        if abs(pan) < .002 and abs(tilt) < .002:
            if self.active:
                self.output.stop()
            self.active = False
        else:
            self.output.move(pan, tilt, 0)
            self.active = True
