from pathlib import Path
import unittest
import numpy as np
from PIL import Image
from vtrack.detector import PersonDetector, model_path


@unittest.skipUnless(model_path().exists(), 'Instale o modelo: python -m scripts.fetch_models')
class DetectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = PersonDetector(size=640)

    def test_actual_inference_on_blank_frame(self):
        self.assertEqual(self.detector.detect(Image.new('RGB', (640, 480))), [])

    def test_coordinate_decode_clips_padding_and_filters_other_classes(self):
        raw = np.zeros((1, 8400, 85), dtype='float32')
        # Stride-8 anchor (20,20): center at (164,164), box (128,96).
        index = 20 * 80 + 20
        raw[0, index, :4] = [.5, .5, np.log(16), np.log(12)]
        raw[0, index, 4:6] = [.9, .9]
        result = self.detector.decode(raw, (640, 480), 1)
        self.assertEqual(len(result), 1)
        box, score = result[0]
        self.assertAlmostEqual(box[0], 100 / 640, places=4)
        self.assertAlmostEqual(box[1], 116 / 480, places=4)
        self.assertGreater(score, .8)
        raw[0, index, 6] = 1
        self.assertEqual(self.detector.decode(raw, (640, 480), 1), [])
