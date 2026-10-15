"""Asynchronous person detection and operator-selected appearance lock."""
import threading
import time
import numpy as np
from .tracking import Detection, TargetLock, DigitalFramer, similarity


def signature(frame, box):
    import cv2
    image = np.asarray(frame.convert('RGB'))
    x, y, width, height = box
    left, top = max(0, int(x * frame.width)), max(0, int(y * frame.height))
    right, bottom = min(frame.width, int((x + width) * frame.width)), min(frame.height, int((y + height) * frame.height))
    crop = image[top:bottom, left:right]
    if crop.size == 0:
        return ()
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    vectors = []
    for stripe in np.array_split(hsv, 3, axis=0):
        if not stripe.size:
            return ()
        hist = cv2.calcHist([stripe], [0, 1], None, [12, 8], [0, 180, 0, 256]).flatten()
        norm = np.linalg.norm(hist)
        vectors.extend((hist / norm if norm else hist).tolist())
    return tuple(vectors)


class VisionWorker:
    def __init__(self, provider, size=416):
        self.provider = provider
        self.input_size = size
        self.lock = TargetLock(threshold=.9, margin=.08)
        self.framer = DigitalFramer()
        self.detections = []
        self.target = None
        self.timestamp = 0
        self.error = None
        self.detector_name = 'A iniciar detector'
        self.generation = 0
        self.mutex = threading.Lock()
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def _run(self):
        try:
            import cv2
            from .detector import PersonDetector, HOGDetector
            try:
                detector = PersonDetector(size=self.input_size)
            except FileNotFoundError:
                detector = HOGDetector()
            self.detector_name = detector.name
            previous = None
            while not self.stop.wait(.12):
                frame, captured = self.provider()
                now = time.monotonic()
                if frame is None or now - captured > .6:
                    with self.mutex:
                        self.target = self.lock.update([])
                        self.detections = []
                    continue
                if captured == previous:
                    continue
                previous = captured
                generation = self.generation
                predictions = detector.detect(frame)
                detections = [Detection(box, signature(frame, box), confidence) for box, confidence in predictions]
                with self.mutex:
                    if generation != self.generation:
                        continue
                    self.detections = detections
                    self.target = self.lock.update(detections)
                    self.timestamp = captured
        except Exception as error:
            self.error = f'Detector indisponível: {type(error).__name__}'

    def select_at(self, x, y):
        with self.mutex:
            candidates = [d for d in self.detections if d.box[0] <= x <= d.box[0] + d.box[2] and d.box[1] <= y <= d.box[1] + d.box[3]]
            if time.monotonic() - self.timestamp > .6:
                raise ValueError('Imagem de deteção antiga; aguarde um quadro recente')
            if not candidates:
                raise ValueError('Clique numa pessoa dentro de uma caixa de deteção')
            chosen = min(candidates, key=lambda d: d.box[2] * d.box[3])
            self.generation += 1
            self.lock.select(chosen)
            self.target = chosen

    def snapshot(self):
        with self.mutex:
            target = self.target if time.monotonic() - self.timestamp < .6 else None
            return (list(self.detections) if time.monotonic() - self.timestamp < .6 else []), target, self.lock.state, self.lock.reference, self.timestamp

    def adopt(self, reference):
        with self.mutex:
            self.generation += 1
            self.lock.reference = reference
            self.lock.state = 'lost'
            self.lock.target = self.target = None
            self.lock.streak = 0

    def close(self):
        self.stop.set()
        self.worker.join(timeout=3)


class CameraRouter:
    """Opt-in experimental handoff, fresh unique match + five observations + cooldown."""
    def __init__(self):
        self.pending = None
        self.count = 0
        self.last_switch = -10
        self.last_sample = None

    def choose(self, current, reference, snapshots, now):
        current_target = snapshots.get(current, ([], None, '', None, 0))[1]
        if current_target is not None or reference is None or now - self.last_switch < 3:
            self.pending, self.count = None, 0
            return None
        candidates = []
        for camera, (detections, target, state, _, timestamp) in snapshots.items():
            if camera == current or now - timestamp > .6:
                continue
            for detection in detections:
                candidates.append((similarity(reference, detection.signature), camera, timestamp))
        candidates.sort(reverse=True)
        if not candidates or candidates[0][0] < .96 or (len(candidates) > 1 and candidates[0][0] - candidates[1][0] < .06):
            self.pending, self.count = None, 0
            return None
        _, camera, sample = candidates[0]
        if camera != self.pending:
            self.pending, self.count, self.last_sample = camera, 0, None
        if sample != self.last_sample:
            self.count += 1
            self.last_sample = sample
        if self.count >= 5:
            self.last_switch = now
            self.pending, self.count = None, 0
            return camera
        return None
