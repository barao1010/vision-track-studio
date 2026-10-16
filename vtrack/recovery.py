"""Recoverable media resources; stale video is never presented as current capture."""
import threading
import time
from .audio import PCMBuffer


class RecoveringVideo:
    def __init__(self, factory, stale_after=2., startup_timeout=8., retry_min=.5, retry_max=8.):
        self.factory = factory
        self.stale_after, self.startup_timeout = stale_after, startup_timeout
        self.retry_min, self.retry_max = retry_min, retry_max
        self.current = None
        self.error = 'A ligar à fonte de vídeo'
        self.restarts = 0
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    @property
    def timestamp(self):
        current = self.current
        return current.timestamp if current else 0

    def frame(self):
        current = self.current
        if current is None or time.monotonic() - current.timestamp > self.stale_after:
            return None
        return current.frame()

    def _run(self):
        delay = self.retry_min
        while not self.stop.is_set():
            current = None
            try:
                current = self.factory()
                self.current = current
                started = time.monotonic()
                while not self.stop.wait(.05):
                    now = time.monotonic()
                    stamp = current.timestamp
                    process = getattr(current, 'process', None)
                    if process is not None and process.poll() is not None:
                        raise OSError('Captura terminada')
                    if (not stamp and now - started > self.startup_timeout) or (stamp and now - stamp > self.stale_after):
                        raise TimeoutError('Captura sem imagens recentes')
                    self.error = None if stamp else 'A aguardar a primeira imagem'
                    if stamp and now - started > 10:
                        delay = self.retry_min
            except Exception as error:
                self.error = f'Vídeo sem sinal ({type(error).__name__}); a religar'
            finally:
                self.current = None
                if current:
                    current.close()
            if self.stop.is_set():
                break
            self.restarts += 1
            if self.stop.wait(delay):
                break
            delay = min(self.retry_max, delay * 2)

    def close(self):
        self.stop.set()
        self.worker.join(timeout=6)


class RecoveringAudio:
    def __init__(self, factory, retry_min=1., retry_max=8.):
        self.factory = factory
        self.buffer = PCMBuffer()
        self.error = 'A ligar à fonte de áudio'
        self.stop = threading.Event()
        self.current = None
        self.retry_min, self.retry_max = retry_min, retry_max
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def _run(self):
        delay = self.retry_min
        while not self.stop.is_set():
            current = None
            try:
                current = self.factory()
                self.current = current
                started = time.monotonic()
                last_data = started
                while not self.stop.wait(.02):
                    if current.error:
                        raise OSError('Fonte áudio terminada')
                    with current.buffer.lock:
                        available = len(current.buffer.data)
                    if available:
                        self.buffer.push(current.buffer.pull(min(available, 4800)))
                        last_data = time.monotonic()
                        self.error = None
                    if time.monotonic() - last_data > 8:
                        raise TimeoutError('Áudio sem amostras')
                    if time.monotonic() - started > 10:
                        delay = self.retry_min
            except Exception as error:
                self.error = f'Áudio sem sinal ({type(error).__name__}); a religar'
            finally:
                self.current = None
                if current:
                    current.close()
                with self.buffer.lock:
                    self.buffer.data = self.buffer.data[:0]
            if self.stop.wait(delay):
                break
            delay = min(self.retry_max, delay * 2)

    def close(self):
        self.stop.set()
        self.worker.join(timeout=6)
