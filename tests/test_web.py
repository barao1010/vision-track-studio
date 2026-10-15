from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import threading
import time
import unittest
from vtrack.capture import WebSource


@unittest.skipUnless(os.environ.get('VISION_TRACK_TEST_WEB') == '1', 'Ative VISION_TRACK_TEST_WEB=1 após instalar Chromium')
class WebTests(unittest.TestCase):
    def test_browser_transparency_and_custom_css(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body style="margin:0;background:transparent"><div id="box" style="width:32px;height:32px;background:red"></div></body></html>')
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        source = WebSource(f'http://127.0.0.1:{server.server_port}', (64, 64), '#box {background: rgb(0, 255, 0) !important;}')
        try:
            deadline = time.monotonic() + 20
            while source.frame() is None and not source.error and time.monotonic() < deadline:
                time.sleep(.1)
            self.assertIsNone(source.error)
            frame = source.frame()
            self.assertIsNotNone(frame)
            self.assertEqual(frame.getpixel((10, 10)), (0, 255, 0, 255))
            self.assertEqual(frame.getpixel((50, 50))[3], 0)
        finally:
            source.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertFalse(source.worker.is_alive())
