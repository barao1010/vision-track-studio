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

if __name__ == "__main__":
    unittest.main()
