import unittest
from cinema_controller import CinemaPTZController
from test_ptz_target_controller import MockPTZ

class CinemaTests(unittest.TestCase):
    def test_headroom_uses_top_of_body_not_face_center(self):
        ptz = MockPTZ()
        c = CinemaPTZController(ptz)
        c.update(1000, 1000, (400, 120, 200, 700), (0, 0), 1)
        self.assertEqual([], ptz.commands)

    def test_speed_limit_and_immediate_hold_stop(self):
        ptz = MockPTZ()
        c = CinemaPTZController(ptz, max_speed=.15)
        for n in range(30):
            c.update(1000, 1000, (800, 120, 100, 500), (.8, 0), 1+n*.1)
        self.assertTrue(all(abs(cmd[1]) <= .15 for cmd in ptz.commands if cmd[0] == 'move'))
        c.stop()
        self.assertEqual(('stop',), ptz.commands[-1])
        self.assertEqual([0., 0.], c.v)

    def test_suave_accelerates_slower_than_dynamic(self):
        speeds = []
        for preset in ('suave', 'dinamico'):
            ptz = MockPTZ()
            c = CinemaPTZController(ptz, preset)
            c.update(1000, 1000, (800, 120, 100, 500), (0, 0), 1)
            speeds.append(ptz.commands[-1][1])
        self.assertLess(speeds[0], speeds[1])
