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


class PCMValidationTests(unittest.TestCase):
    def test_page_binding_rejects_invalid_or_unbounded_audio(self):
        from vtrack.audio import PCMBuffer
        from vtrack.web_audio import accept_pcm
        buffer = PCMBuffer()
        self.assertFalse(accept_pcm(buffer, [float('nan'), 0]))
        self.assertFalse(accept_pcm(buffer, [0] * 9000))
        self.assertFalse(accept_pcm(buffer, [1]))
        self.assertTrue(accept_pcm(buffer, [2, -2]))
        self.assertEqual(buffer.pull(1).tolist(), [[1., -1.]])


@unittest.skipUnless(os.environ.get('VISION_TRACK_TEST_WEB') == '1', 'Chromium necessário')
class WebAudioTests(unittest.TestCase):
    def test_html_media_audio_reaches_pcm_buffer(self):
        import io, wave
        import numpy as np
        pcm = (.3 * np.sin(np.arange(48000) * 2 * np.pi * 440 / 48000) * 32767).astype('<i2')
        encoded = io.BytesIO()
        with wave.open(encoded, 'wb') as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(48000)
            handle.writeframes(pcm.tobytes())
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                if self.path.startswith('/tone.wav'):
                    self.send_header('Content-Type', 'audio/wav')
                    self.end_headers()
                    self.wfile.write(encoded.getvalue())
                else:
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'<html><body><audio src="/tone.wav" autoplay loop></audio></body></html>')
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        source = WebSource(f'http://127.0.0.1:{server.server_port}', (64, 64), audio=True)
        peak = 0
        try:
            deadline = time.monotonic() + 20
            while peak < .1 and not source.error and time.monotonic() < deadline:
                samples = source.buffer.pull(960)
                peak = max(peak, float(np.abs(samples).max()))
                time.sleep(.02)
            self.assertIsNone(source.error)
            self.assertGreater(peak, .1)
        finally:
            source.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
