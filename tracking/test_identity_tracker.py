import unittest
from identity_tracker import IdentityTracker, similarity

class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.tracker = IdentityTracker()
        self.box = (100, 100, 80, 200)
        self.sig = [.2, .4, .8] * 9
        self.tracker.select(self.box, self.sig, 1)

    def test_unselected_person_never_replaces_original(self):
        self.assertIsNone(self.tracker.update([self.box], [[.9, .1, .1]*9], 1.1, 1))
        self.assertEqual(self.sig, list(self.tracker.signature))
        self.assertEqual(self.box, self.tracker.box)

    def test_temporary_loss_retains_selection_and_needs_three_new_frames(self):
        self.tracker.update([], [], 1.1, 1)
        self.assertIsNone(self.tracker.update([self.box], [self.sig], 1.2, 2))
        self.assertIsNone(self.tracker.update([self.box], [self.sig], 1.2, 2))
        self.assertIsNone(self.tracker.update([self.box], [self.sig], 1.3, 3))
        self.assertIsNotNone(self.tracker.update([self.box], [self.sig], 1.4, 4))
        self.assertEqual('locked', self.tracker.state)

    def test_crossing_lookalike_cannot_take_over_when_original_leaves(self):
        other = (105, 100, 80, 200)
        self.assertIsNone(self.tracker.update([self.box, other], [self.sig, self.sig], 1.1, 1))
        for n in range(2, 10):
            self.assertIsNone(self.tracker.update([other], [self.sig], 1+n*.1, n))
        self.assertEqual(self.box, self.tracker.box)
        self.assertEqual('ambiguous', self.tracker.state)

    def test_signature_does_not_drift(self):
        changed = [.21, .41, .79]*9
        self.assertIsNotNone(self.tracker.update([self.box], [changed], 1.1, 1))
        self.assertEqual(self.sig, list(self.tracker.signature))

    def test_non_finite_signature_is_rejected(self):
        self.assertEqual(0, similarity([float('nan')]*3, [1]*3))
