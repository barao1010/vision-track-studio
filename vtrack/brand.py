"""Product identity drawn from basic geometric primitives."""
from PIL import Image, ImageDraw


def icon(size=256):
    scale = size / 100
    image = Image.new('RGBA', (size, size), '#0b1018')
    drawing = ImageDraw.Draw(image)
    def point(x, y):
        return round(x * scale), round(y * scale)
    drawing.line([point(16, 24), point(49, 83)], fill='#3187ff', width=max(1, round(17 * scale)))
    drawing.line([point(49, 83), point(78, 36)], fill='#6bb6ff', width=max(1, round(17 * scale)))
    drawing.line([point(65, 12), point(90, 12), point(90, 39)], fill='#6bb6ff', width=max(1, round(5 * scale)))
    return image
