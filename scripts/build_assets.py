from pathlib import Path
from vtrack.brand import icon
root = Path('assets')
root.mkdir(exist_ok=True)
image = icon(512)
image.save(root / 'vision-track.png')
image.save(root / 'vision-track.ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
