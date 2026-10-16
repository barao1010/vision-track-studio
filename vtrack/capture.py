"""Windows device inputs and offscreen web sources."""
import io
import os
import re
import subprocess
import threading
import time
from urllib.parse import urlparse
from PIL import Image
from .media import ffmpeg, spawn, Decoder


def devices():
    if os.name != 'nt':
        raise RuntimeError('A lista DirectShow está disponível no Windows')
    result = spawn([ffmpeg(), '-hide_banner', '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    _, data = result.communicate(timeout=15)
    return [(name, kind) for name, kind in re.findall(r'"(.+?)" \((video|audio)\)', data.decode(errors='replace'))]


def video_input(kind, value, fps=25):
    if kind == 'camera':
        if os.name != 'nt':
            raise RuntimeError('Captura USB DirectShow requer Windows')
        return ['-f', 'dshow', '-i', f'video={value}']
    if kind in {'desktop', 'window'}:
        if os.name != 'nt':
            raise RuntimeError('Captura GDI requer Windows')
        return ['-f', 'gdigrab', '-framerate', str(fps), '-i', 'desktop' if kind == 'desktop' else f'title={value}']
    if kind == 'rtsp':
        return ['-rtsp_transport', 'tcp', '-rw_timeout', '5000000', '-i', value]
    return ['-re', '-stream_loop', '-1', '-i', value]


def audio_input(kind, value):
    if kind == 'microphone':
        if os.name != 'nt':
            raise RuntimeError('Captura DirectShow requer Windows')
        return ['-f', 'dshow', '-i', f'audio={value}']
    return video_input(kind, value)


class WebSource:
    def __init__(self, url, size, css='', audio=True):
        if urlparse(url).scheme not in {'http', 'https'}:
            raise ValueError('Use um endereço HTTP ou HTTPS')
        from .audio import PCMBuffer
        self.buffer = PCMBuffer()
        self.audio_enabled = audio
        self.url, self.size, self.css = url, size, css
        self.latest = None
        self.timestamp = 0
        self.error = None
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def _run(self):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as runtime:
                browser = runtime.chromium.launch(headless=True, args=['--autoplay-policy=no-user-gesture-required'])
                try:
                    page = browser.new_page(viewport={'width': self.size[0], 'height': self.size[1]})
                    if self.audio_enabled:
                        from .web_audio import SCRIPT, accept_pcm
                        page.expose_binding('__visionTrackAudio', lambda source, samples: accept_pcm(self.buffer, samples))
                        page.add_init_script(SCRIPT)
                    page.goto(self.url, wait_until='domcontentloaded', timeout=8000)
                    if self.css:
                        page.add_style_tag(content=self.css)
                    while not self.stop.is_set():
                        data = page.screenshot(omit_background=True, timeout=3000)
                        with Image.open(io.BytesIO(data)) as opened:
                            self.latest = opened.convert('RGBA')
                        self.timestamp = time.monotonic()
                        page.wait_for_timeout(50)
                finally:
                    browser.close()
        except Exception as error:
            self.error = f'Fonte web indisponível ({type(error).__name__}). Instale Chromium: python -m playwright install chromium'

    def frame(self):
        return self.latest

    def close(self):
        self.stop.set()
        self.worker.join(timeout=12)
