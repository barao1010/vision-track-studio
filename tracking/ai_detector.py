"""GPL-2.0-or-later. Person detector using the Apache-2.0 OpenCV Zoo YOLOX model."""
from pathlib import Path
import cv2
import numpy as np
from yolox import YoloX


class PersonDetector:
    def __init__(self):
        model = Path(__file__).resolve().parent / "models/object_detection_yolox_2022nov.onnx"
        self.detector = YoloX(str(model), confThreshold=.55, nmsThreshold=.45)

    def detect(self, frame):
        h, w = frame.shape[:2]
        scale = min(640 / w, 640 / h)
        resized = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (int(w * scale), int(h * scale)))
        padded = np.full((640, 640, 3), 114, dtype=np.float32)
        padded[:resized.shape[0], :resized.shape[1]] = resized
        people = []
        for detection in self.detector.infer(padded):
            if int(detection[-1]) != 0:
                continue
            x, y, bw, bh = detection[:4] / scale
            x, y = max(0, x), max(0, y)
            bw, bh = min(w - x, bw), min(h - y, bh)
            if bw >= 24 and bh >= 24:
                people.append((int(x), int(y), int(bw), int(bh)))
        return people



from association import distinct_match
