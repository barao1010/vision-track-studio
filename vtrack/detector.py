"""YOLOX person inference for the pinned OpenCV Zoo model.

The decoding equations follow the published YOLOX tensor layout (grid/stride,
logarithmic width/height). This is a new adapter, not an imported studio engine.
Model provenance and license are in models/README.md and LICENSE-YOLOX.txt.
"""
from pathlib import Path
import hashlib
import os
import sys
import numpy as np

MODEL_SHA256 = 'c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063'


def model_path():
    override = os.environ.get('VISION_TRACK_MODEL')
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    return Path(override) if override else root / 'models/person-yolox.onnx'


class PersonDetector:
    name = 'YOLOX / OpenCV DNN'
    def __init__(self, path=None, threshold=.45, size=416):
        import cv2
        cv2.setNumThreads(max(1, min(2, os.cpu_count() or 1)))
        path = Path(path) if path else model_path()
        if not path.exists():
            raise FileNotFoundError('Modelo YOLOX em falta: execute python -m scripts.fetch_models')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != MODEL_SHA256:
            raise ValueError('O modelo YOLOX não corresponde ao checksum aprovado')
        if size not in {320, 416, 640}:
            raise ValueError('Use resolução de deteção 320, 416 ou 640')
        self.input_size = size
        self.threshold = threshold
        self.net = cv2.dnn.readNetFromONNX(str(path))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.grid = []
        self.stride = []
        for step in (8, 16, 32):
            side = self.input_size // step
            self.grid.extend((column, row) for row in range(side) for column in range(side))
            self.stride.extend([step] * (side * side))
        self.grid = np.array(self.grid, dtype='float32')
        self.stride = np.array(self.stride, dtype='float32')[:, None]

    def decode(self, raw, original_size, scale):
        import cv2
        data = np.asarray(raw).reshape(-1, 85)
        if len(data) != len(self.grid):
            raise ValueError('Formato de saída YOLOX incompatível')
        classes = np.argmax(data[:, 5:], axis=1)
        scores = data[:, 4] * data[:, 5]
        mask = (classes == 0) & (scores >= self.threshold) & np.all(np.isfinite(data[:, :6]), axis=1)
        if not mask.any():
            return []
        values = data[mask]
        centers = (values[:, :2] + self.grid[mask]) * self.stride[mask]
        dimensions = np.exp(np.clip(values[:, 2:4], -10, 10)) * self.stride[mask]
        boxes = np.concatenate(((centers - dimensions / 2) / scale, dimensions / scale), axis=1)
        width, height = original_size
        # Clip letterbox/padding detections to real input pixels before NMS.
        corners = boxes[:, :2] + boxes[:, 2:]
        boxes[:, 0] = np.clip(boxes[:, 0], 0, width)
        boxes[:, 1] = np.clip(boxes[:, 1], 0, height)
        corners[:, 0] = np.clip(corners[:, 0], 0, width)
        corners[:, 1] = np.clip(corners[:, 1], 0, height)
        boxes[:, 2:] = corners - boxes[:, :2]
        scores = scores[mask]
        indices = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), self.threshold, .45)
        result = []
        for index in np.asarray(indices).reshape(-1):
            x, y, box_width, box_height = boxes[index]
            if box_width > 2 and box_height > 4:
                result.append(((float(x / width), float(y / height), float(box_width / width), float(box_height / height)), float(scores[index])))
        return result

    def detect(self, frame):
        import cv2
        rgb = np.asarray(frame.convert('RGB'))
        scale = min(self.input_size / frame.width, self.input_size / frame.height)
        width, height = max(1, int(frame.width * scale)), max(1, int(frame.height * scale))
        padded = np.full((self.input_size, self.input_size, 3), 114, dtype='float32')
        # This model takes unnormalised RGB 0..255 with top-left letterboxing.
        padded[:height, :width] = cv2.resize(rgb, (width, height))
        blob = np.ascontiguousarray(padded.transpose(2, 0, 1)[None])
        self.net.setInput(blob)
        output = self.net.forward()
        return self.decode(output, frame.size, scale)


class HOGDetector:
    name = 'HOG (fallback; instale o modelo YOLOX)'
    def __init__(self):
        import cv2
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame):
        import cv2
        image = frame.copy()
        image.thumbnail((640, 480))
        if image.width < 64 or image.height < 128:
            return []
        pixels = cv2.cvtColor(np.asarray(image.convert('RGB')), cv2.COLOR_RGB2BGR)
        boxes, weights = self.hog.detectMultiScale(pixels, winStride=(8, 8), padding=(8, 8), scale=1.05)
        return [((x / image.width, y / image.height, w / image.width, h / image.height), float(score)) for (x, y, w, h), score in zip(boxes, weights)]
