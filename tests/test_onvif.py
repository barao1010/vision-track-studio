from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import base64
import hashlib
import threading
import unittest
from xml.etree import ElementTree as ET
from vtrack.ptz import Protocol


class ONVIFTests(unittest.TestCase):
    def test_discovery_digest_motion_and_camera_generated_preset_token(self):
        actions = []
        authenticated = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                root = ET.fromstring(self.rfile.read(int(self.headers['Content-Length'])))
                elements = {node.tag.split('}')[-1]: node for node in root.iter()}
                nonce = base64.b64decode(elements['Nonce'].text)
                created = elements['Created'].text
                digest = base64.b64encode(hashlib.sha1(nonce + created.encode() + b'secret').digest()).decode()
                authenticated.append(elements['Password'].text == digest)
                operation = list(elements['Body'])[0]
                action = operation.tag.split('}')[-1]
                actions.append((action, ET.tostring(operation).decode()))
                base = f'http://127.0.0.1:{self.server.server_port}'
                bodies = {
                    'GetCapabilities': f'<tt:Capabilities><tt:Media><tt:XAddr>{base}/media</tt:XAddr></tt:Media><tt:PTZ><tt:XAddr>{base}/ptz</tt:XAddr></tt:PTZ></tt:Capabilities>',
                    'GetProfiles': '<Profiles token="profile1"/>',
                    'GetPresets': '<Preset token="old-token"><tt:Name>First</tt:Name></Preset>',
                    'SetPreset': '<PresetToken>camera-token-2</PresetToken>',
                }
                namespace = operation.tag.split('}')[0][1:]
                response = f'<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:tt="http://www.onvif.org/ver10/schema"><s:Body><{action}Response xmlns="{namespace}">{bodies.get(action, "")}</{action}Response></s:Body></s:Envelope>'
                self.send_response(200)
                self.end_headers()
                self.wfile.write(response.encode())
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        protocol = None
        try:
            protocol = Protocol({'protocol': 'ONVIF', 'host': '127.0.0.1', 'port': server.server_port, 'username': 'operator', 'password': 'secret'})
            protocol.move(.2, -.1, .3)
            protocol.move(0, 0, 0)
            protocol.preset(2, save=True)
            protocol.preset(2)
            self.assertEqual(protocol.presets[2], 'camera-token-2')
            self.assertIn('camera-token-2', actions[-1][1])
            self.assertTrue(all(authenticated))
            self.assertIn('ContinuousMove', [action for action, _ in actions])
            self.assertIn('Stop', [action for action, _ in actions])
        finally:
            if protocol:
                protocol.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
