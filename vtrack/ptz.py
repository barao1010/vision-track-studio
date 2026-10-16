"""Original protocol encoders, transports and deadman controller."""
import base64
import hashlib
import math
import os
import queue
import socket
import struct
import threading
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape


def clamp(value):
    if not math.isfinite(value):
        raise ValueError('Velocidade inválida')
    return max(-1., min(1., value))


def visca_move(pan, tilt, address=1):
    pan, tilt = clamp(pan), clamp(tilt)
    return bytes([0x80 | address, 1, 6, 1, max(1, round(abs(pan) * 24)), max(1, round(abs(tilt) * 20)),
        2 if pan > 0 else 1 if pan < 0 else 3, 1 if tilt > 0 else 2 if tilt < 0 else 3, 255])


def visca_zoom(zoom, address=1):
    zoom = clamp(zoom)
    speed = min(7, round(abs(zoom) * 7))
    return bytes([0x80 | address, 1, 4, 7, (0x20 if zoom > 0 else 0x30) | speed if zoom else 0, 255])


def pelco(pan=0., tilt=0., zoom=0., address=1, preset=None, save=False):
    pan, tilt, zoom = clamp(pan), clamp(tilt), clamp(zoom)
    if not 1 <= address <= 255:
        raise ValueError('Endereço Pelco inválido')
    command = (2 if pan > 0 else 4 if pan < 0 else 0) | (8 if tilt > 0 else 16 if tilt < 0 else 0) | (0x20 if zoom > 0 else 0x40 if zoom < 0 else 0)
    first, second = round(abs(pan) * 63), round(abs(tilt) * 63)
    if preset is not None:
        if not 1 <= preset <= 255:
            raise ValueError('Preset inválido')
        command, first, second = (3 if save else 7), 0, preset
    body = bytes([address, 0, command, first, second])
    return b'\xff' + body + bytes([sum(body) & 255])


class Protocol:
    def __init__(self, config):
        self.config = config
        self.kind = config['protocol']
        self.address = int(config.get('address', 1))
        self.sequence = 0
        self.serial = self.sock = None
        self.last_zoom = None
        self.presets = {}
        if not 1 <= self.address <= 7 and self.kind.startswith('VISCA'):
            raise ValueError('Endereço VISCA deve ser de 1 a 7')
        if self.kind in {'VISCA Serial', 'Pelco-D Serial'}:
            import serial
            self.serial = serial.Serial(config['serial'], int(config.get('baud', 9600)), timeout=.1, write_timeout=.3)
        elif self.kind == 'VISCA IP':
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(.3)
            self.destination = (config['host'], int(config.get('port', 52381)))
        elif self.kind == 'Pelco-D TCP':
            self.sock = socket.create_connection((config['host'], int(config.get('port', 4001))), timeout=.5)
        elif self.kind == 'ONVIF':
            self._onvif_setup()
        else:
            raise ValueError('Protocolo inválido')

    def _send(self, payload):
        if self.serial:
            self.serial.write(payload)
        elif self.kind == 'VISCA IP':
            self.sequence = (self.sequence + 1) & 0xffffffff
            self.sock.sendto(struct.pack('!HHI', 0x0100, len(payload), self.sequence) + payload, self.destination)
        else:
            self.sock.sendall(payload)

    def move(self, pan, tilt, zoom=0):
        pan, tilt, zoom = clamp(pan), clamp(tilt), clamp(zoom)
        if self.kind == 'ONVIF':
            if not any((pan, tilt, zoom)):
                self._soap(self.ptz_url, 'Stop', f'<ProfileToken>{escape(self.profile)}</ProfileToken><PanTilt>true</PanTilt><Zoom>true</Zoom>')
            else:
                self._soap(self.ptz_url, 'ContinuousMove', f'<ProfileToken>{escape(self.profile)}</ProfileToken><Velocity><tt:PanTilt x="{pan}" y="{tilt}"/><tt:Zoom x="{zoom}"/></Velocity><Timeout>PT0.5S</Timeout>')
        elif self.kind.startswith('VISCA'):
            self._send(visca_move(pan, tilt, self.address))
            if zoom != self.last_zoom:
                self._send(visca_zoom(zoom, self.address))
                self.last_zoom = zoom
        else:
            self._send(pelco(pan, tilt, zoom, self.address))

    def preset(self, number, save=False):
        if not 1 <= number <= 16:
            raise ValueError('Use preset de 1 a 16')
        if self.kind == 'ONVIF':
            token = self.presets.get(number, '')
            if save:
                result = self._soap(self.ptz_url, 'SetPreset', f'<ProfileToken>{escape(self.profile)}</ProfileToken><PresetName>Preset {number}</PresetName>{('<PresetToken>' + escape(token) + '</PresetToken>') if token else ''}')
                returned = next((n.text for n in result.iter() if n.tag.endswith('}PresetToken')), None)
                if returned:
                    self.presets[number] = returned
            else:
                if not token:
                    raise ValueError('Preset ONVIF ainda não existe')
                self._soap(self.ptz_url, 'GotoPreset', f'<ProfileToken>{escape(self.profile)}</ProfileToken><PresetToken>{escape(token)}</PresetToken>')
        elif self.kind.startswith('VISCA'):
            self._send(bytes([0x80 | self.address, 1, 4, 0x3f, 1 if save else 2, number - 1, 255]))
        else:
            self._send(pelco(address=self.address, preset=number, save=save))

    def _soap(self, endpoint, action, body, namespace='http://www.onvif.org/ver20/ptz/wsdl'):
        nonce = os.urandom(16)
        created = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        password = self.config.get('password', '')
        digest = base64.b64encode(hashlib.sha1(nonce + created.encode() + password.encode()).digest()).decode()
        security = f'''<wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"><wsse:UsernameToken><wsse:Username>{escape(self.config.get('username', ''))}</wsse:Username><wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest}</wsse:Password><wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{base64.b64encode(nonce).decode()}</wsse:Nonce><wsu:Created>{created}</wsu:Created></wsse:UsernameToken></wsse:Security>'''
        envelope = f'<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:tt="http://www.onvif.org/ver10/schema"><s:Header>{security}</s:Header><s:Body><{action} xmlns="{namespace}">{body}</{action}></s:Body></s:Envelope>'
        request = Request(endpoint, envelope.encode(), {'Content-Type': f'application/soap+xml; charset=utf-8; action="{namespace}/{action}"'})
        with urlopen(request, timeout=.5) as response:
            document = response.read(1024 * 1024)
        root = ET.fromstring(document)
        if any(node.tag.endswith('}Fault') for node in root.iter()):
            raise RuntimeError('A câmera rejeitou o comando ONVIF')
        return root

    def _onvif_setup(self):
        endpoint = self.config.get('endpoint') or f'http://{self.config["host"]}:{self.config.get("port", 80)}/onvif/device_service'
        capabilities = self._soap(endpoint, 'GetCapabilities', '<Category>All</Category>', 'http://www.onvif.org/ver10/device/wsdl')
        media_url = None
        self.ptz_url = None
        for node in capabilities.iter():
            if node.tag.endswith('}Media'):
                media_url = next((n.text for n in node if n.tag.endswith('}XAddr')), None)
            if node.tag.endswith('}PTZ'):
                self.ptz_url = next((n.text for n in node if n.tag.endswith('}XAddr')), None)
        if not media_url or not self.ptz_url:
            raise RuntimeError('Serviço PTZ ONVIF indisponível')
        profiles = self._soap(media_url, 'GetProfiles', '', 'http://www.onvif.org/ver10/media/wsdl')
        self.profile = self.config.get('profile') or next((n.attrib['token'] for n in profiles.iter() if n.tag.endswith('}Profiles') and 'token' in n.attrib), None)
        if not self.profile:
            raise RuntimeError('Perfil ONVIF não encontrado')
        existing = self._soap(self.ptz_url, 'GetPresets', f'<ProfileToken>{escape(self.profile)}</ProfileToken>')
        tokens = [n.attrib['token'] for n in existing.iter() if n.tag.endswith('}Preset') and 'token' in n.attrib]
        self.presets = dict(enumerate(tokens[:16], start=1))

    def close(self):
        try:
            self.move(0, 0, 0)
        finally:
            if self.serial:
                self.serial.close()
            if self.sock:
                self.sock.close()


class PTZSession:
    """No network I/O on UI thread; stale commands trigger stop in <=350 ms + I/O."""
    def __init__(self, config, factory=Protocol):
        self.config, self.factory = config, factory
        self.velocity = (0, 0, 0)
        self.updated = 0
        self.lock = threading.Lock()
        self.actions = queue.Queue(maxsize=4)
        self.stop = threading.Event()
        self.error = None
        self.connected = False
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def move(self, pan, tilt, zoom=0):
        with self.lock:
            self.velocity = tuple(clamp(value) for value in (pan, tilt, zoom))
            self.updated = time.monotonic()

    def preset(self, number, save=False):
        self.move(0, 0, 0)
        self.actions.put_nowait((number, save))

    def _run(self):
        protocol = None
        try:
            protocol = self.factory(self.config)
            self.connected = True
            last = None
            sent = 0
            while not self.stop.wait(.03):
                now = time.monotonic()
                with self.lock:
                    desired = self.velocity if now - self.updated < .35 else (0, 0, 0)
                if desired != last or (any(desired) and now - sent > .15):
                    protocol.move(*desired)
                    last, sent = desired, now
                try:
                    number, save = self.actions.get_nowait()
                except queue.Empty:
                    continue
                protocol.move(0, 0, 0)
                protocol.preset(number, save)
                last = (0, 0, 0)
        except Exception as error:
            self.error = f'PTZ: {type(error).__name__}: ligação/comando falhou'
        finally:
            self.connected = False
            if protocol:
                try:
                    protocol.close()
                except Exception:
                    pass

    def close(self):
        self.stop.set()
        self.worker.join(timeout=2)


class CameraControlBank:
    """Session-only camera mappings. Passwords are never written to project JSON."""
    def __init__(self, factory=PTZSession):
        self.factory = factory
        self.configs = {}
        self.camera = None
        self.session = None

    def configure(self, camera, config):
        self.configs[camera] = dict(config)

    def activate(self, camera, allowed=False):
        if self.camera == camera and self.session is not None and allowed:
            return self.session
        self.deactivate()
        self.camera = camera
        if allowed and camera in self.configs:
            self.session = self.factory(self.configs[camera])
        return self.session

    def deactivate(self):
        if self.session:
            self.session.close()
        self.session = None
        self.camera = None
