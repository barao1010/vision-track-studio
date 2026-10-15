"""Windows WinMM joystick polling. No device access until explicitly enabled."""
import ctypes
import os


class JOYINFOEX(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in ('size', 'flags', 'x', 'y', 'z', 'r', 'u', 'v', 'buttons', 'button_number', 'pov', 'reserved1', 'reserved2')]


class Joystick:
    def __init__(self, device=0, deadzone=.15):
        if os.name != 'nt':
            raise RuntimeError('Joystick WinMM requer Windows')
        self.device, self.deadzone = device, deadzone
        self.api = ctypes.WinDLL('winmm')
        self.api.joyGetPosEx.argtypes = [ctypes.c_uint, ctypes.POINTER(JOYINFOEX)]
        self.api.joyGetPosEx.restype = ctypes.c_uint

    def poll(self):
        state = JOYINFOEX()
        state.size = ctypes.sizeof(state)
        state.flags = 0xff
        if self.api.joyGetPosEx(self.device, ctypes.byref(state)):
            raise RuntimeError('Joystick desligado; movimento parado')
        def axis(value):
            normalized = (value - 32767.5) / 32767.5
            return 0 if abs(normalized) < self.deadzone else max(-1., min(1., normalized))
        # Zoom on buttons 1/2 avoids unexpected motion on uncalibrated third axis.
        zoom = .4 if state.buttons & 1 else -.4 if state.buttons & 2 else 0
        return axis(state.x) * .6, -axis(state.y) * .6, zoom
