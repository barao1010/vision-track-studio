"""Download the hash-pinned Apache-2.0 YOLOX model from OpenCV Zoo."""
import hashlib
from pathlib import Path
import urllib.request

destination = Path(__file__).resolve().parent.parent / "tracking/models"
destination.mkdir(exist_ok=True)
model = destination / "object_detection_yolox_2022nov.onnx"
expected = "c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063"
if not model.exists() or hashlib.sha256(model.read_bytes()).hexdigest() != expected:
    data = urllib.request.urlopen("https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/object_detection_yolox/object_detection_yolox_2022nov.onnx", timeout=120).read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError("Tracking model checksum mismatch")
    model.write_bytes(data)
print("Verified OpenCV Zoo YOLOX model.")
