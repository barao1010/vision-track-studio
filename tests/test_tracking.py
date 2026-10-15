import unittest
from vtrack.tracking import Detection, TargetLock, DigitalFramer


class TrackingTests(unittest.TestCase):
    def test_loss_requires_three_consistent_confirmations(self):
        target = Detection((.2, .3, .1, .2), (1, 0))
        lock = TargetLock()
        self.assertIsNone(lock.update([target]))
        lock.select(target)
        self.assertIsNone(lock.update([]))
        self.assertIsNone(lock.update([target]))
        self.assertIsNone(lock.update([target]))
        self.assertEqual(lock.update([target]), target)

    def test_crossing_stops_and_preserves_original_identity(self):
        original = Detection((.2, .3, .1, .2), (1, 0))
        similar = Detection((.22, .3, .1, .2), (.99, .01))
        stranger = Detection((.2, .3, .1, .2), (0, 1))
        lock = TargetLock()
        lock.select(original)
        self.assertIsNone(lock.update([original, similar]))
        self.assertEqual(lock.state, 'ambiguous')
        self.assertIsNone(lock.update([stranger]))
        self.assertEqual(lock.reference, (1, 0))

    def test_recovery_cannot_combine_distant_candidates(self):
        lock = TargetLock()
        lock.select(Detection((.1, .1, .1, .1), (1, 0)))
        lock.update([])
        for x in [.1, .8, .1, .8]:
            self.assertIsNone(lock.update([Detection((x, .1, .1, .1), (1, 0))]))

    def test_framing_remains_inside_image_and_holds_on_loss(self):
        framer = DigitalFramer('Dinâmico')
        for _ in range(100):
            crop = framer.update((.95, .95, .05, .05), .04)
            self.assertGreaterEqual(crop[0], 0)
            self.assertLessEqual(crop[0] + crop[2], 1)
        self.assertEqual(framer.update(None, .04), crop)
        with self.assertRaises(ValueError):
            framer.update(None, float('nan'))


class ContinuityTests(unittest.TestCase):
    def test_locked_identity_cannot_jump_across_frame_immediately(self):
        lock = TargetLock()
        original = Detection((.1, .1, .1, .2), (1, 0))
        distant = Detection((.8, .1, .1, .2), (1, 0))
        lock.select(original)
        self.assertIsNone(lock.update([distant]))
        self.assertIsNone(lock.update([distant]))
        self.assertEqual(lock.update([distant]), distant)

    def test_ambiguous_recovery_requires_five_frames(self):
        lock = TargetLock()
        target = Detection((.1, .1, .1, .2), (1, 0))
        similar = Detection((.12, .1, .1, .2), (.99, .01))
        lock.select(target)
        self.assertIsNone(lock.update([target, similar]))
        for _ in range(4):
            self.assertIsNone(lock.update([target]))
        self.assertEqual(lock.update([target]), target)
