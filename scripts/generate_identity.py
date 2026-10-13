"""GPL-2.0-or-later. Draw deterministic Vision Track Studio application icons."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw

root = Path(sys.argv[1]).resolve()
image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((8, 8, 248, 248), radius=52, fill="#071A3D")
draw.rounded_rectangle((38, 63, 189, 193), radius=20, fill="#1261A8", outline="white", width=7)
draw.polygon([(196, 98), (228, 81), (228, 175), (196, 159)], fill="white")
draw.line([(65, 97), (89, 159), (113, 97)], fill="white", width=10, joint="curve")
draw.line([(120, 99), (171, 99)], fill="white", width=10)
draw.line([(146, 99), (146, 158)], fill="white", width=10)
draw.ellipse((58, 177, 70, 189), fill="#2D8FD5")
image.save(root / "frontend/forms/images/obs.png")
image.save(root / "frontend/cmake/windows/obs-studio.ico", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("Vision Track Studio icons generated.")
