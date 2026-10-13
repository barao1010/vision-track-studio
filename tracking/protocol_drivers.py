"""GPL-2.0-or-later. Native adapters for Vision Track AI PTZ protocols."""
import socket
import struct
import threading
import time

class WirePTZ:
    def __init__(self, config):
        self.kind = config['protocol']
        self.host = config.get('host', '')
        self.port = int(config.get('port') or (52381 if self.kind == 'visca_ip' else 4001))
        self.serial_port = config.get('serial', '')
        self.baud = int(config.get('baud') or (2400 if self.kind == 'pelco_d' else 9600))
        self.address = int(config.get('address', 1))
        if not 1 <= self.address <= 255:
            raise ValueError('Invalid camera address')
        self.pan_invert = bool(config.get('invertPan'))
        self.tilt_invert = bool(config.get('invertTilt'))
        self.sequence = 0
        self.lock = threading.Lock()
        self.deadline = None
        self.closed = threading.Event()
        self.connection = None
        if self.kind == 'visca_ip':
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        elif self.serial_port:
            import serial
            self.connection = serial.Serial(self.serial_port, self.baud, timeout=.2, write_timeout=.5)
        elif self.kind == 'pelco_d':
            self.connection = socket.create_connection((self.host, self.port), timeout=2)
        else:
            raise ValueError('Serial port required')
        self.stop()
        self.timer = threading.Thread(target=self._watchdog, daemon=True)
        self.timer.start()

    def _watchdog(self):
        while not self.closed.wait(.05):
            with self.lock:
                if self.deadline is not None and time.monotonic() >= self.deadline:
                    try:
                        self._stop()
                    except Exception:
                        self.closed.set()
                    self.deadline = None

    def _send(self, packet):
        if self.kind == 'visca_ip':
            self.sequence = (self.sequence+1) & 0xffffffff
            packet = struct.pack('>HHI', 0x0100, len(packet), self.sequence) + packet
            self.connection.sendto(packet, (self.host, self.port))
        elif hasattr(self.connection, 'write'):
            self.connection.write(packet)
        else:
            self.connection.sendall(packet)

    def _pelco(self, c2, d1=0, d2=0, c1=0):
        parts = [self.address, c1, c2, d1, d2]
        return bytes([255] + parts + [sum(parts) % 256])

    def _zoom(self, z):
        if self.kind == 'pelco_d':
            return self._pelco(0x20 if z > .02 else 0x40 if z < -.02 else 0)
        value = 0 if abs(z) < .02 else (0x20 if z > 0 else 0x30) | max(0, min(7, int(abs(z)*7)))
        return bytes([0x81, 1, 4, 7, value, 255])

    def _stop(self):
        if self.kind == 'pelco_d':
            self._send(self._pelco(0))
        else:
            self._send(bytes([0x81, 1, 6, 1, 1, 1, 3, 3, 255]))
            self._send(self._zoom(0))

    def stop(self):
        with self.lock:
            self.deadline = None
            self._stop()

    def move(self, pan, tilt, zoom):
        pan = -pan if self.pan_invert else pan
        tilt = tilt if self.tilt_invert else -tilt
        pan, tilt, zoom = [max(-1, min(1, v)) for v in (pan, tilt, zoom)]
        with self.lock:
            if self.kind == 'pelco_d':
                direction = (2 if pan > .02 else 4 if pan < -.02 else 0) | (8 if tilt > .02 else 16 if tilt < -.02 else 0)
                direction |= 0x20 if zoom > .02 else 0x40 if zoom < -.02 else 0
                self._send(self._pelco(direction, int(abs(pan)*63), int(abs(tilt)*63)))
            else:
                self._send(bytes([0x81, 1, 6, 1, max(1, int(abs(pan)*24)), max(1, int(abs(tilt)*20)), 3 if abs(pan)<.02 else 2 if pan>0 else 1, 3 if abs(tilt)<.02 else 1 if tilt>0 else 2, 255]))
                self._send(self._zoom(zoom))
            self.deadline = time.monotonic()+.5

    def preset(self, number, save=False):
        number = int(number)
        if not 0 <= number <= (127 if self.kind != 'pelco_d' else 255):
            raise ValueError('Invalid preset')
        with self.lock:
            self.deadline = None
            self._stop()
            self._send(self._pelco(3 if save else 7, 0, number) if self.kind == 'pelco_d' else bytes([0x81, 1, 4, 0x3f, 1 if save else 2, number, 255]))

    def home(self):
        if self.kind == 'pelco_d':
            raise ValueError('Pelco-D does not provide home')
        with self.lock:
            self.deadline = None
            self._stop()
            self._send(bytes([0x81, 1, 6, 4, 255]))

    def close(self):
        try:
            self.stop()
        finally:
            self.closed.set()
            self.connection.close()


def create_camera(config, username, password):
    if config.get('protocol', 'onvif') == 'onvif':
        from ptz_companion import OnvifPTZ
        return OnvifPTZ(config['ptz'], config['profile'], username, password,
                        invert_pan=config.get('invertPan', False), invert_tilt=config.get('invertTilt', True))
    return WirePTZ(config)
