import unittest
from ptz_target_controller import Box, TargetPTZController

class MockPTZ:
    def __init__(self):
        self.commands = []
    def move(self, pan, tilt, zoom):
        self.commands.append(("move", pan, tilt, zoom))
    def stop(self):
        self.commands.append(("stop",))

class TargetControllerTests(unittest.TestCase):
    def test_does_not_move_without_selection(self):
        ptz = MockPTZ()
        controller = TargetPTZController(ptz)
        controller.update(1920, 1080, {1: Box(1400, 300, 200, 400)}, now=1)
        self.assertEqual([], ptz.commands)

    def test_tracks_selected_id_only(self):
        ptz = MockPTZ()
        controller = TargetPTZController(ptz)
        controller.select(1)
        controller.update(1920, 1080, {2: Box(1500, 200, 200, 300), 1: Box(100, 300, 200, 300)}, now=1)
        self.assertLess(ptz.commands[-1][1], 0)

    def test_stops_after_target_loss(self):
        ptz = MockPTZ()
        controller = TargetPTZController(ptz)
        controller.select(3)
        controller.update(100, 100, {3: Box(65, 45, 15, 15)}, now=1)
        controller.update(100, 100, {}, now=2)
        self.assertEqual(("stop",), ptz.commands[-1])

    def test_no_repeated_stop_when_target_remains_lost(self):
        ptz = MockPTZ()
        controller = TargetPTZController(ptz)
        controller.select(1)
        controller.update(100, 100, {1: Box(65, 45, 15, 15)}, now=1)
        controller.update(100, 100, {}, now=2)
        count = len(ptz.commands)
        controller.update(100, 100, {}, now=3)
        self.assertEqual(count, len(ptz.commands))

    def test_switch_target_resets_throttle(self):
        ptz = MockPTZ()
        controller = TargetPTZController(ptz)
        controller.select(1)
        controller.update(100, 100, {1: Box(65, 45, 15, 15)}, now=1)
        controller.select(2)
        controller.update(100, 100, {2: Box(5, 45, 15, 15)}, now=1.01)
        self.assertLess(ptz.commands[-1][1], 0)

    def test_centered_target_stops_without_residual_motion(self):
        ptz = MockPTZ()
        controller = TargetPTZController(ptz)
        controller.select(1)
        controller.update(100, 100, {1: Box(80, 40, 20, 20)}, now=1)
        controller.update(100, 100, {1: Box(40, 40, 20, 20)}, now=1.01)
        self.assertEqual(("stop",), ptz.commands[-1])
        count = len(ptz.commands)
        controller.update(100, 100, {1: Box(40, 40, 20, 20)}, now=2)
        self.assertEqual(count, len(ptz.commands))

    def test_invalid_box_resets_motion_before_direction_change(self):
        for invalid in (Box(10, 10, 0, 20), Box(float('nan'), 10, 20, 20)):
            with self.subTest(invalid=invalid):
                ptz = MockPTZ()
                controller = TargetPTZController(ptz)
                controller.select(1)
                controller.update(100, 100, {1: Box(80, 40, 20, 20)}, now=1)
                controller.update(100, 100, {1: invalid}, now=1.01)
                self.assertEqual(("stop",), ptz.commands[-1])
                controller.update(100, 100, {1: Box(0, 40, 20, 20)}, now=1.02)
                self.assertLess(ptz.commands[-1][1], 0)

if __name__ == "__main__":
    unittest.main()

