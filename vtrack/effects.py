"""Original image adjustments, keying and block-based audio effects."""
import math
import numpy as np
from PIL import Image, ImageColor, ImageEnhance


def video_effects(image, settings):
    brightness = float(settings.get('brightness', 1))
    contrast = float(settings.get('contrast', 1))
    if brightness != 1:
        image = ImageEnhance.Brightness(image).enhance(max(0, min(3, brightness)))
    if contrast != 1:
        image = ImageEnhance.Contrast(image).enhance(max(0, min(3, contrast)))
    key = settings.get('chroma', '')
    if key:
        color = np.array(ImageColor.getrgb(key)[:3], dtype=np.float32)
        data = np.array(image.convert('RGBA'))
        distance = np.linalg.norm(data[:, :, :3].astype(np.float32) - color, axis=2)
        threshold = max(0, min(255, float(settings.get('chroma_threshold', 80))))
        blend = np.clip((distance - threshold) / 30, 0, 1)
        data[:, :, 3] = (data[:, :, 3] * blend).astype(np.uint8)
        image = Image.fromarray(data)
    return image


class AudioEffects:
    def __init__(self):
        self.delay = np.zeros((0, 2), dtype=np.float32)
        self.delay_size = 0

    def apply(self, block, settings):
        delay_size = round(max(0, min(2000, float(settings.get('delay_ms', 0)))) * 48)
        if delay_size != self.delay_size:
            self.delay = np.zeros((delay_size, 2), dtype=np.float32)
            self.delay_size = delay_size
        if delay_size:
            combined = np.concatenate((self.delay, block))
            self.delay = combined[len(block):]
            block = combined[:len(block)].copy()
        gate = float(settings.get('gate_db', -120))
        if gate > -120 and len(block):
            rms = float(np.sqrt(np.mean(block * block)))
            if rms < 10 ** (max(-120, min(0, gate)) / 20):
                block = np.zeros_like(block)
        threshold_db = float(settings.get('compressor_db', 0))
        if threshold_db < 0:
            threshold = 10 ** (max(-60, threshold_db) / 20)
            ratio = max(1, min(20, float(settings.get('compressor_ratio', 4))))
            magnitude = np.abs(block)
            compressed = threshold * np.power(np.maximum(magnitude, threshold) / threshold, 1 / ratio)
            block = np.where(magnitude > threshold, np.sign(block) * compressed, block)
        return block
