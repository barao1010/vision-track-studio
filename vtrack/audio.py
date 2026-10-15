"""Bounded PCM buffers, scene-aware mixer, and external audio capture."""
from dataclasses import dataclass, field
import threading
import numpy as np
from .media import ffmpeg, spawn

RATE = 48000
CHANNELS = 2


class PCMBuffer:
    def __init__(self, capacity=RATE):
        self.data = np.zeros((0, 2), dtype=np.float32)
        self.capacity = capacity
        self.lock = threading.Lock()
        self.overruns = 0
        self.underruns = 0

    def push(self, samples):
        samples = np.asarray(samples, dtype=np.float32).reshape(-1, 2)
        with self.lock:
            joined = np.concatenate((self.data, samples))
            if len(joined) > self.capacity:
                self.overruns += len(joined) - self.capacity
            self.data = joined[-self.capacity:]

    def pull(self, count):
        result = np.zeros((count, 2), dtype=np.float32)
        with self.lock:
            available = min(count, len(self.data))
            result[:available] = self.data[:available]
            self.data = self.data[available:]
            self.underruns += count - available
        return result


@dataclass
class Channel:
    buffer: PCMBuffer = field(default_factory=PCMBuffer)
    gain: float = 1.0
    muted: bool = False
    active: bool = True
    peak: float = 0.0
    rms: float = 0.0
    settings: dict = field(default_factory=dict)
    effects: object = None


class Mixer:
    def __init__(self):
        self.channels = {}
        self.lock = threading.Lock()
        self.master = 1.0
        self.clipped = 0

    def add(self, key, buffer):
        with self.lock:
            from .effects import AudioEffects
            self.channels[key] = Channel(buffer, effects=AudioEffects())

    def remove(self, key):
        with self.lock:
            self.channels.pop(key, None)

    def mix(self, count):
        result = np.zeros((count, 2), dtype=np.float32)
        with self.lock:
            channels = list(self.channels.values())
        for channel in channels:
            block = channel.buffer.pull(count)
            # Always drain inactive sources, so scene changes do not replay stale audio.
            if channel.muted or not channel.active:
                channel.effects.apply(np.zeros_like(block), channel.settings)
                channel.peak = channel.rms = 0.0
                continue
            block = channel.effects.apply(block, channel.settings)
            block *= max(0, min(4, channel.gain))
            channel.peak = float(np.max(np.abs(block))) if count else 0.0
            channel.rms = float(np.sqrt(np.mean(block * block))) if count else 0.0
            result += block
        result *= max(0, min(4, self.master))
        self.clipped += int(np.count_nonzero(np.abs(result) > 1))
        return np.clip(result, -1, 1)


class AudioCapture:
    def __init__(self, input_args):
        self.buffer = PCMBuffer()
        self.error = None
        self.stopping = False
        self.process = spawn([ffmpeg(), '-nostdin', '-loglevel', 'error', *input_args,
            '-vn', '-ac', '2', '-ar', str(RATE), '-f', 'f32le', 'pipe:1'],
            stdout=__import__('subprocess').PIPE, stderr=__import__('subprocess').DEVNULL)
        self.worker = threading.Thread(target=self._read, daemon=True)
        self.worker.start()

    def _read(self):
        length = 960 * 2 * 4
        while not self.stopping:
            data = bytearray()
            while len(data) < length:
                part = self.process.stdout.read(length - len(data))
                if not part:
                    if not self.stopping:
                        self.error = 'Fonte de áudio sem sinal ou sem faixa de áudio'
                    return
                data.extend(part)
            self.buffer.push(np.frombuffer(data, dtype='<f4').reshape(-1, 2))

    def close(self):
        self.stopping = True
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except __import__('subprocess').TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.worker.join(timeout=2)
        self.process.stdout.close()


class Monitor:
    def __init__(self):
        import sounddevice as sd
        self.buffer = PCMBuffer(capacity=4800)
        def callback(outdata, frames, timing, status):
            outdata[:] = self.buffer.pull(frames)
        self.stream = sd.OutputStream(samplerate=RATE, channels=2, dtype='float32', callback=callback)
        self.stream.start()

    def close(self):
        self.stream.stop()
        self.stream.close()


class SystemCapture:
    """Explicit WASAPI loopback source, converted to the mixer rate."""
    def __init__(self):
        import os
        if os.name != 'nt':
            raise RuntimeError('Captura do som do sistema requer Windows/WASAPI')
        import pyaudiowpatch as pa
        self.api = pa.PyAudio()
        self.buffer = PCMBuffer()
        self.error = None
        self.stop = threading.Event()
        try:
            info = self.api.get_default_wasapi_loopback()
            self.rate = int(info['defaultSampleRate'])
            self.channels = min(2, int(info['maxInputChannels']))
            if self.channels < 1:
                raise RuntimeError('Dispositivo loopback sem canais')
            self.stream = self.api.open(format=pa.paFloat32, channels=self.channels, rate=self.rate,
                input=True, input_device_index=info['index'], frames_per_buffer=max(1, self.rate // 50))
        except Exception:
            self.api.terminate()
            raise
        self.worker = threading.Thread(target=self._read, daemon=True)
        self.worker.start()

    def _read(self):
        try:
            count = max(1, self.rate // 50)
            while not self.stop.is_set():
                data = self.stream.read(count, exception_on_overflow=False)
                block = np.frombuffer(data, dtype='<f4').reshape(-1, self.channels)
                if self.channels == 1:
                    block = np.repeat(block, 2, axis=1)
                if self.rate != RATE:
                    # Fixed 20 ms blocks; output and input rates are integral here.
                    positions = np.linspace(0, len(block) - 1, 960)
                    block = np.column_stack([np.interp(positions, np.arange(len(block)), block[:, channel]) for channel in range(2)])
                self.buffer.push(block)
        except Exception as error:
            if not self.stop.is_set():
                self.error = f'WASAPI: {type(error).__name__}'

    def close(self):
        self.stop.set()
        self.stream.stop_stream()
        self.worker.join(timeout=2)
        self.stream.close()
        self.api.terminate()
