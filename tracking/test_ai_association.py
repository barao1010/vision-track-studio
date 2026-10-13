"""Regression checks for selected-person association without model downloads."""
import unittest
from association import distinct_match


class AssociationTests(unittest.TestCase):
    def test_overlapping_people_require_reselection(self):
        self.assertIsNone(distinct_match((0, 0, 100, 100), [(0, 0, 100, 100), (10, 0, 100, 100)]))

    def test_unrelated_person_does_not_take_target(self):
        self.assertIsNone(distinct_match((0, 0, 100, 100), [(500, 0, 100, 100)]))

    def test_single_distinct_person_matches(self):
        self.assertEqual((0, 0, 100, 100), distinct_match((0, 0, 100, 100), [(0, 0, 100, 100)]))
