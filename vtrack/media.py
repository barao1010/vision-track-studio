"""External FFmpeg transport. No shell commands and no bundled codecs."""
from collections import deque
from pathlib import Path
import os
import queue
import shutil
import subprocess
import threading
import time
from PIL import Image


def ffmpeg():
    path = os.environ.get('VISION_TRACK_FFMPEG') or shutil.which('ffmpeg')
    if not path:
        raise RuntimeError('Instale FFmpeg ou defina VISION_TRACK_FFMPEG')
    if os.name == 'nt' and Path(path).parent.name.lower() == 'bin':
        package = Path(os.environ.get('ProgramData', r'C:\ProgramData')) / 'chocolatey/lib/ffmpeg/tools'
        candidates = list(package.glob('**/ffmpeg.exe')) if package.exists() else []
        if candidates:
            path = str(candidates[0])
    return path


def spawn(arguments, **kwargs):
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(arguments, **kwargs)


class Decoder:
    def __init__(self, value, size, network=False, input_args=None):
        self.size = size
        self.latest = None
        self.timestamp = 0
        self.error = None
        self.lock = threading.Lock()
        self.stopping = False
        options = ['-rtsp_transport', 'tcp', '-rw_timeout', '5000000'] if network else ['-re', '-stream_loop', '-1']
        inputs = input_args if input_args is not None else [*options, '-i', value]
        self.process = spawn([ffmpeg(), '-nostdin', '-loglevel', 'error', *inputs, '-an', '-vf', f'scale={size[0]}:{size[1]}', '-pix_fmt', 'rgb24',
            '-f', 'rawvideo', 'pipe:1'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.worker = threading.Thread(target=self._read, daemon=True)
        self.worker.start()

    def _read(self):
        length = self.size[0] * self.size[1] * 3
        while not self.stopping:
            data = bytearray()
            while len(data) < length:
                part = self.process.stdout.read(length - len(data))
                if not part:
                    self.error = 'Fluxo de vídeo terminou ou não está acessível'
                    return
                data.extend(part)
            with self.lock:
                self.latest = Image.frombytes('RGB', self.size, bytes(data))
                self.timestamp = time.monotonic()

    def frame(self):
        with self.lock:
            return self.latest

    def close(self):
        self.stopping = True
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.worker.join(timeout=2)
        self.process.stdout.close()


class VideoOutput:
    """Bounded queue; a stalled encoder never blocks the UI. Video only in this milestone."""
    def __init__(self, destination, size, fps, live=False, encoder='libx264'):
        if live and not destination.startswith(('rtmp://', 'rtmps://')):
            raise ValueError('Endereço RTMP inválido')
        self.size, self.fps = size, fps
        self.frames = queue.Queue(maxsize=4)
        self.dropped = 0
        self.error = None
        self.logs = deque(maxlen=20)
        self.closed = False
        if not live and Path(destination).exists():
            raise FileExistsError('O ficheiro de destino já existe')
        codec = ['-c:v', encoder, '-b:v', '4500k', '-g', str(fps * 2)] if live else ['-c:v', 'mpeg4', '-q:v', '3']
        self.process = spawn([ffmpeg(), '-nostdin', '-hide_banner', '-loglevel', 'error',
            '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}',
            '-r', str(fps), '-i', 'pipe:0', '-an', *codec, '-pix_fmt', 'yuv420p',
            '-f', 'flv' if live else 'matroska', destination], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        self.log_worker = threading.Thread(target=self._logs, daemon=True)
        self.log_worker.start()
        self.worker = threading.Thread(target=self._write, daemon=True)
        self.worker.start()

    def _logs(self):
        for line in iter(self.process.stderr.readline, b''):
            self.logs.append(line.decode(errors='replace').strip())

    def submit(self, frame):
        if self.closed or self.error:
            return
        if frame.size != self.size:
            raise ValueError('Formato de frame incompatível')
        try:
            self.frames.put_nowait(frame.convert('RGB').tobytes())
        except queue.Full:
            self.dropped += 1

    def _write(self):
        try:
            while True:
                data = self.frames.get()
                if data is None:
                    break
                self.process.stdin.write(data)
        except (BrokenPipeError, OSError) as error:
            self.error = str(error)
        finally:
            try:
                self.process.stdin.close()
            except OSError:
                pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        deadline = time.monotonic() + 5
        while self.worker.is_alive():
            try:
                self.frames.put(None, timeout=.1)
                break
            except queue.Full:
                if time.monotonic() > deadline:
                    self.process.kill()
                    break
        self.worker.join(timeout=5)
        try:
            result = self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            result = self.process.wait()
            self.error = 'Tempo de finalização excedido'
        self.log_worker.join(timeout=1)
        self.process.stderr.close()
        if result:
            self.error = self.error or ('\n'.join(self.logs) or f'FFmpeg terminou com código {result}')
        if self.error:
            raise RuntimeError(self.error)
