# SPDX-License-Identifier: GPL-2.0-or-later
import unittest
from frame_inbox import FrameInbox


class TestFrameInbox(unittest.TestCase):
    def test_slow_detector_always_gets_latest_frame(self):
        inbox = FrameInbox()
        for frame in range(1000):
            inbox.put(frame)
        self.assertEqual(inbox.frames.qsize(), 1)
        self.assertEqual(inbox.read(), (True, 999))

    def test_shutdown_wakes_waiting_capture_and_rejects_late_frames(self):
        inbox = FrameInbox()
        inbox.put(1)
        inbox.release()
        inbox.put(2)
        self.assertEqual(inbox.read(), (False, None))
        self.assertFalse(inbox.isOpened())
