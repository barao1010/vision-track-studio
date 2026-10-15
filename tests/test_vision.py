import unittest
from PIL import Image
from vtrack.tracking import Detection
from vtrack.vision import CameraRouter, signature


class VisionTests(unittest.TestCase):
    def test_signature_discriminates_different_color(self):
        a = signature(Image.new('RGB', (64, 128), 'red'), (0, 0, 1, 1))
        b = signature(Image.new('RGB', (64, 128), 'blue'), (0, 0, 1, 1))
        from vtrack.tracking import similarity
        self.assertAlmostEqual(similarity(a, a), 1)
        self.assertLess(similarity(a, b), .2)

    def test_handoff_requires_five_fresh_samples_and_unique_identity(self):
        router = CameraRouter()
        candidate = Detection((.2, .2, .2, .5), (1, 0))
        for tick in range(4):
            now = 10 + tick / 10
            snapshots = {'a': ([], None, 'lost', (1, 0), now), 'b': ([candidate], None, 'unselected', None, now)}
            self.assertIsNone(router.choose('a', (1, 0), snapshots, now))
            self.assertIsNone(router.choose('a', (1, 0), snapshots, now))
        now = 10.4
        snapshots['b'] = ([candidate], None, '', None, now)
        self.assertEqual(router.choose('a', (1, 0), snapshots, now), 'b')

    def test_ambiguous_cameras_never_handoff(self):
        router = CameraRouter()
        detection = Detection((0, 0, 1, 1), (1, 0))
        for tick in range(20):
            now = 10 + tick / 10
            snapshots = {key: ([detection], None, '', None, now) for key in ('b', 'c')}
            self.assertIsNone(router.choose('a', (1, 0), snapshots, now))
