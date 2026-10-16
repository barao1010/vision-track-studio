# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded, latest-frame handoff from the existing OBS capture pipeline."""
import queue


class FrameInbox:
    def __init__(self):
        self.frames = queue.Queue(maxsize=1)
        self.closed = False

    def put(self, frame):
        if self.closed:
            return
        try:
            self.frames.get_nowait()
        except queue.Empty:
            pass
        try:
            self.frames.put_nowait(frame)
        except queue.Full:
            pass

    def read(self):
        try:
            frame = self.frames.get(timeout=4)
        except queue.Empty:
            return False, None
        return frame is not None, frame

    def isOpened(self):
        return not self.closed

    def release(self):
        self.closed = True
        self.put_closed()

    def put_closed(self):
        try:
            self.frames.get_nowait()
        except queue.Empty:
            pass
        try:
            self.frames.put_nowait(None)
        except queue.Full:
            pass
