"""GPL-2.0-or-later. Tests for fixed-camera digital framing."""
import math
import unittest
from digital_zoom import DigitalZoomController


class TestDigitalZoom(unittest.TestCase):
    def test_centered_target(self):
        z = DigitalZoomController()
        crop = z.update(640, 360, (288, 90, 64, 100))
        self.assertIsNotNone(crop)
        self.assertGreater(crop["zoom"], 1)
        self.assertLessEqual(crop["zoom"], 2.7)

    def test_edges_never_exceed_input(self):
        z = DigitalZoomController(max_zoom=4)
        for box in [(0, 0, 45, 45), (600, 310, 40, 50)]:
            for _ in range(15):
                c = z.update(640, 360, box)
                self.assertGreaterEqual(c["left"], -1e-6)
                self.assertGreaterEqual(c["top"], -1e-6)
                self.assertLessEqual(c["left"]+c["width"], 1.000001)
                self.assertLessEqual(c["top"]+c["height"], 1.000001)

    def test_smooth_transition(self):
        z = DigitalZoomController(smoothing=.12)
        z.update(640, 360, (280, 100, 100, 90))
        first = z.zoom
        z.update(640, 360, (500, 150, 30, 30))
        self.assertGreater(z.zoom, first)
        self.assertLess(z.zoom, z.max_zoom)

    def test_invalid_boxes_and_reset(self):
        z = DigitalZoomController()
        self.assertIsNone(z.update(0, 360, (0, 0, 10, 10)))
        self.assertIsNone(z.update(640, 360, (0, 0, math.nan, 10)))
        z.update(640, 360, (100, 100, 70, 100))
        z.reset()
        self.assertEqual(z.zoom, 1.)
        self.assertFalse(z.locked)

    def test_full_frame_for_large_subject(self):
        z = DigitalZoomController()
        c = z.update(1920, 1080, (400, 40, 900, 900))
        self.assertEqual(c["zoom"], 1.)
        self.assertAlmostEqual(c["left"], 0.)


if __name__ == "__main__":
    unittest.main()
