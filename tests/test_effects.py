from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
from vtrack.effects import AudioEffects, video_effects
from vtrack.plugins import VideoPlugin


class EffectsTests(unittest.TestCase):
    def test_chroma_key_and_preserved_nonkey_pixels(self):
        frame = Image.new('RGBA', (16, 16), '#00ff00')
        frame.putpixel((0, 0), (255, 0, 0, 255))
        output = video_effects(frame, {'chroma': '#00ff00', 'chroma_threshold': 60})
        self.assertEqual(output.getpixel((8, 8))[3], 0)
        self.assertEqual(output.getpixel((0, 0)), (255, 0, 0, 255))

    def test_gate_compression_and_exact_delay(self):
        effects = AudioEffects()
        quiet = np.ones((960, 2), dtype='float32') * .001
        self.assertTrue(np.all(effects.apply(quiet, {'gate_db': -40}) == 0))
        loud = np.ones((960, 2), dtype='float32') * .9
        self.assertLess(float(effects.apply(loud, {'compressor_db': -12}).max()), .5)
        impulse = np.zeros((960, 2), dtype='float32')
        impulse[0] = 1
        self.assertEqual(effects.apply(impulse, {'delay_ms': 20}).max(), 0)
        self.assertEqual(effects.apply(np.zeros_like(impulse), {'delay_ms': 20})[0, 0], 1)

    def test_explicit_plugin_and_invalid_output_disables_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'effect.py'
            path.write_text('VISION_TRACK_API=1\ndef process_video(image, context):\n return image.transpose(0)\n')
            plugin = VideoPlugin(path)
            frame = Image.new('RGBA', (16, 16), 'blue')
            frame.putpixel((0, 0), (255, 0, 0, 255))
            self.assertEqual(plugin.apply(frame, {}).getpixel((15, 0)), (255, 0, 0, 255))
            path.write_text('VISION_TRACK_API=1\ndef process_video(image, context):\n return None\n')
            broken = VideoPlugin(path)
            self.assertIs(broken.apply(frame, {}), frame)
            self.assertTrue(broken.disabled)
            self.assertIsNotNone(broken.error)
