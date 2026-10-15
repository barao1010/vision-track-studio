"""Fetch the pinned public model, verify SHA-256, then replace atomically."""
import hashlib
from pathlib import Path
import tempfile
from urllib.request import urlopen
from vtrack.detector import MODEL_SHA256

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://media.githubusercontent.com/media/opencv/opencv_zoo/47534e27c9851bb1128ccc0102f1145e27f23f98/models/object_detection_yolox/object_detection_yolox_2022nov.onnx'
TARGET = ROOT / 'models/person-yolox.onnx'

def main():
    TARGET.parent.mkdir(exist_ok=True)
    if TARGET.exists() and hashlib.sha256(TARGET.read_bytes()).hexdigest() == MODEL_SHA256:
        print('Modelo YOLOX já verificado')
        return
    temporary = None
    try:
        digest = hashlib.sha256()
        total = 0
        with tempfile.NamedTemporaryFile(dir=TARGET.parent, delete=False) as output:
            temporary = Path(output.name)
            with urlopen(URL, timeout=30) as response:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    total += len(block)
                    if total > 40_000_000:
                        raise ValueError('Modelo excede o tamanho esperado')
                    output.write(block)
                    digest.update(block)
        if total != 35858002 or digest.hexdigest() != MODEL_SHA256:
            raise ValueError('Checksum ou tamanho do modelo inválido')
        temporary.replace(TARGET)
        print('Modelo YOLOX descarregado e verificado')
    finally:
        if temporary and temporary.exists():
            temporary.unlink()

if __name__ == '__main__':
    main()
