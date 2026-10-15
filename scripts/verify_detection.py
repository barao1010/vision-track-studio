"""Check inference on a public, fixed OpenCV test image (not a live camera)."""
import hashlib
import io
from urllib.request import urlopen
from PIL import Image
from vtrack.detector import PersonDetector

URL = 'https://raw.githubusercontent.com/opencv/opencv/4.11.0/samples/data/basketball1.png'
SHA256 = 'ba06f6701f7260998b430c39b6557f775497e6ce7b1a74f0b7ea6af371bf54a6'

def main():
    with urlopen(URL, timeout=30) as response:
        data = response.read(3_000_000)
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('A amostra OpenCV não corresponde ao checksum esperado')
    with Image.open(io.BytesIO(data)) as opened:
        frame = opened.convert('RGB')
    results = PersonDetector().detect(frame)
    if len(results) < 2 or not all(score >= .45 for _, score in results):
        raise AssertionError('YOLOX não detetou as duas pessoas na amostra OpenCV')
    print(f'YOLOX: {len(results)} pessoas na imagem pública; isto não é validação de câmera física')

if __name__ == '__main__':
    main()
