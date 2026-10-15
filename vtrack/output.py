"""A/V output with one monotonic clock and two local FFmpeg input sockets."""
from collections import deque
from pathlib import Path
import socket
import subprocess
import threading
import time
import numpy as np
from PIL import Image
from .audio import RATE
from .media import ffmpeg, spawn


class AVOutput:
    def __init__(self, destination, size, fps, live=False, encoder='libx264'):
        if live and not destination.startswith(('rtmp://', 'rtmps://')):
            raise ValueError('URL RTMP inválida')
        if not live and Path(destination).exists():
            raise FileExistsError('O ficheiro já existe')
        self.size, self.fps = size, fps
        self.error = None
        self.dropped = 0
        self.duplicates = 0
        self.latest = Image.new('RGB', size).tobytes()
        self.audio = deque()
        self.audio_samples = 0
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.ready = threading.Barrier(2)
        self.logs = deque(maxlen=20)
        self.servers = []
        self.connections = []
        for _ in range(2):
            server = socket.socket()
            server.bind(('127.0.0.1', 0))
            server.listen(1)
            server.settimeout(10)
            self.servers.append(server)
        urls = [f'tcp://127.0.0.1:{s.getsockname()[1]}' for s in self.servers]
        codec = ['-c:v', encoder, '-b:v', '4500k', '-g', str(fps * 2)] if live else ['-c:v', 'mpeg4', '-q:v', '3']
        command = [ffmpeg(), '-nostdin', '-hide_banner', '-loglevel', 'error', '-n',
            '-thread_queue_size', '64', '-probesize', '32', '-analyzeduration', '0',
            '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', f'{size[0]}x{size[1]}',
            '-framerate', str(fps), '-i', urls[0],
            '-thread_queue_size', '128', '-probesize', '32', '-analyzeduration', '0',
            '-f', 'f32le', '-ar', str(RATE), '-ac', '2', '-i', urls[1],
            '-map', '0:v:0', '-map', '1:a:0', *codec, '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '160k', '-f', 'flv' if live else 'matroska', destination]
        self.process = spawn(command, stderr=subprocess.PIPE)
        self.log_worker = threading.Thread(target=self._logs, daemon=True)
        self.log_worker.start()
        self.workers = [threading.Thread(target=self._send, args=(index,), daemon=True) for index in range(2)]
        self.epoch = None
        for worker in self.workers:
            worker.start()

    def _logs(self):
        for line in iter(self.process.stderr.readline, b''):
            self.logs.append(line.decode(errors='replace').strip())

    def submit(self, frame):
        if frame.size != self.size:
            raise ValueError('Frame incompatível')
        with self.lock:
            self.latest = frame.convert('RGB').tobytes()

    def submit_audio(self, samples):
        with self.lock:
            self.audio.append(np.asarray(samples, dtype='<f4').copy())
            self.audio_samples += len(samples)
            while self.audio_samples > RATE and self.audio:
                self.audio_samples -= len(self.audio.popleft())
                self.dropped += 1

    def _audio_block(self, count):
        result = np.zeros((count, 2), dtype='<f4')
        offset = 0
        with self.lock:
            while offset < count and self.audio:
                block = self.audio.popleft()
                take = min(count - offset, len(block))
                result[offset:offset + take] = block[:take]
                offset += take
                self.audio_samples -= take
                if take < len(block):
                    self.audio.appendleft(block[take:])
        return result.tobytes()

    def _send(self, index):
        try:
            connection, _ = self.servers[index].accept()
            connection.settimeout(3)
            self.connections.append(connection)
            # Raw-video demuxer needs one frame before opening the next input.
            if index == 0:
                connection.sendall(self.latest)
            self.ready.wait(timeout=10)
            with self.lock:
                if self.epoch is None:
                    self.epoch = time.monotonic()
                epoch = self.epoch
            interval = 1 / self.fps if index == 0 else .02
            tick = 1 if index == 0 else 0
            while not self.stop.is_set():
                deadline = epoch + tick * interval
                if self.stop.wait(max(0, deadline - time.monotonic())):
                    break
                if index == 0:
                    with self.lock:
                        data = self.latest
                else:
                    data = self._audio_block(960)
                connection.sendall(data)
                tick += 1
        except (OSError, threading.BrokenBarrierError) as error:
            if not self.stop.is_set():
                self.error = f'Falha na saída A/V: {type(error).__name__}'
                self.stop.set()
                self.ready.abort()
        finally:
            if 'connection' in locals():
                connection.close()

    def close(self):
        self.stop.set()
        self.ready.abort()
        for server in self.servers:
            server.close()
        for worker in self.workers:
            worker.join(timeout=4)
        try:
            result = self.process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.process.kill()
            result = self.process.wait()
        self.log_worker.join(timeout=2)
        self.process.stderr.close()
        if result or self.error:
            raise RuntimeError(self.error or '\n'.join(self.logs) or 'Falha ao finalizar saída')
