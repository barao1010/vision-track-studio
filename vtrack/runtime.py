"""Own runtime connecting media, audio, tracking and output resources."""
import threading
import time
from .audio import Mixer, AudioCapture, SystemCapture
from .capture import video_input, audio_input, WebSource
from .media import Decoder
from .vision import VisionWorker, CameraRouter


class Runtime:
    def __init__(self):
        self.video = {}
        self.audio = {}
        self.vision = {}
        self.outputs = {}
        self.mixer = Mixer()
        self.router = CameraRouter()
        self.selected_camera = None
        self.routed_source = None
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.monitor = None
        self.audio_error = None
        self.audio_worker = threading.Thread(target=self._audio_loop, daemon=True)
        self.audio_worker.start()

    def _audio_loop(self):
        try:
            deadline = time.monotonic()
            while not self.stop.is_set():
                block = self.mixer.mix(960)
                if self.monitor:
                    self.monitor.buffer.push(block)
                with self.lock:
                    outputs = list(self.outputs.values())
                for output in outputs:
                    output.submit_audio(block)
                deadline += .02
                if time.monotonic() - deadline > .2:
                    deadline = time.monotonic()
                self.stop.wait(max(0, deadline - time.monotonic()))
        except Exception as error:
            self.audio_error = f'Motor de áudio: {type(error).__name__}'

    def toggle_monitor(self):
        if self.monitor:
            self.monitor.close()
            self.monitor = None
        else:
            from .audio import Monitor
            self.monitor = Monitor()

    def attach(self, source, fps=25):
        try:
            if source.kind == 'browser':
                self.video[source.id] = WebSource(source.value, (source.width, source.height), source.settings.get('css', ''))
            elif source.kind in {'video', 'rtsp', 'camera', 'desktop', 'window'}:
                self.video[source.id] = Decoder(source.value, (source.width, source.height),
                    input_args=video_input(source.kind, source.value, fps))
            if source.kind in {'audio', 'microphone', 'system_audio'} or source.settings.get('audio', source.kind == 'video'):
                capture = SystemCapture() if source.kind == 'system_audio' else AudioCapture(audio_input(source.kind, source.value))
                self.audio[source.id] = capture
                self.mixer.add(source.id, capture.buffer)
        except Exception:
            self.detach(source.id)
            raise

    def detach(self, key):
        if key in self.vision:
            self.vision.pop(key).close()
        if key in self.video:
            self.video.pop(key).close()
        if key in self.audio:
            self.mixer.remove(key)
            self.audio.pop(key).close()
        if self.selected_camera == key:
            self.selected_camera = None

    def enable_vision(self, key):
        if key not in self.video:
            raise ValueError('Selecione uma fonte de vídeo')
        if key not in self.vision:
            decoder = self.video[key]
            self.vision[key] = VisionWorker(lambda: (decoder.frame(), decoder.timestamp))
        self.selected_camera = key
        self.routed_source = key

    def frames(self, now, digital=False, profile='Cinema', zoom=2., dt=.04, handoff=False):
        frames = {key: decoder.frame() for key, decoder in list(self.video.items())}
        frames = {key: frame for key, frame in frames.items() if frame is not None}
        if handoff and self.selected_camera in self.vision:
            snapshots = {key: worker.snapshot() for key, worker in self.vision.items()}
            reference = snapshots[self.selected_camera][3]
            chosen = self.router.choose(self.selected_camera, reference, snapshots, now)
            if chosen:
                self.vision[chosen].adopt(reference)
                self.selected_camera = chosen
        if digital and self.selected_camera in self.vision and self.selected_camera in frames:
            worker = self.vision[self.selected_camera]
            _, target, _, _, _ = worker.snapshot()
            worker.framer.profile = profile
            frames[self.selected_camera] = worker.framer.render(frames[self.selected_camera], target.box if target else None, dt, zoom)
        if handoff and self.routed_source in frames and self.selected_camera in frames:
            frames[self.routed_source] = frames[self.selected_camera]
        return frames

    def update_audio(self, studio, now):
        weights = {studio.program: 1.}
        if studio.transition:
            start, duration, _, previous = studio.transition
            amount = max(0, min(1, (now - start) / duration))
            weights = {previous: 1 - amount, studio.program: amount}
        active = {}
        for scene in studio.project.scenes:
            for source in scene.sources:
                if source.visible and scene.id in weights:
                    active[source.id] = weights[scene.id]
                channel = self.mixer.channels.get(source.id)
                if channel:
                    channel.active = source.id in active
                    channel.gain = source.settings.get('gain', 1.) * active.get(source.id, 0)
                    channel.muted = source.settings.get('mute', False)
                    channel.settings = dict(source.settings)

    def add_output(self, key, output):
        with self.lock:
            self.outputs[key] = output

    def remove_output(self, key):
        with self.lock:
            output = self.outputs.pop(key)
        output.close()

    def close(self):
        self.stop.set()
        self.audio_worker.join(timeout=2)
        if self.monitor:
            self.monitor.close()
            self.monitor = None
        errors = []
        for key in list(self.outputs):
            try:
                self.remove_output(key)
            except Exception as error:
                errors.append(str(error))
        for key in set(self.video) | set(self.audio):
            self.detach(key)
        return errors
