import time
import unittest
import numpy as np
from vtrack.audio import PCMBuffer
from vtrack.recovery import RecoveringAudio, RecoveringVideo


def until(predicate, seconds=2):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.01)
    return False


class RecoveryTests(unittest.TestCase):
    def test_failed_video_reconnects_and_stale_image_is_hidden(self):
        resources = []
        calls = []
        class Fake:
            def __init__(self):
                self.timestamp = time.monotonic()
                self.closed = False
            def frame(self): return 'frame'
            def close(self): self.closed = True
        def factory():
            calls.append(True)
            if len(calls) == 1:
                raise ConnectionError('Disconnected')
            resource = Fake()
            resources.append(resource)
            return resource
        capture = RecoveringVideo(factory, stale_after=.15, retry_min=.01, retry_max=.02)
        try:
            self.assertTrue(until(lambda: capture.frame() == 'frame'))
            self.assertGreaterEqual(len(calls), 2)
            resources[-1].timestamp = time.monotonic() - 3
            self.assertIsNone(capture.frame())
            self.assertTrue(until(lambda: len(resources) >= 2))
        finally:
            capture.close()
        self.assertFalse(capture.worker.is_alive())
        self.assertTrue(all(resource.closed for resource in resources))

    def test_audio_recovers_with_stable_mixer_buffer(self):
        count = []
        resources = []
        class Fake:
            def __init__(self):
                self.buffer = PCMBuffer()
                self.buffer.push(np.ones((960, 2), dtype='float32') * .25)
                self.error = None
                self.closed = False
            def close(self): self.closed = True
        def factory():
            count.append(True)
            if len(count) == 1:
                raise ConnectionError()
            resource = Fake()
            resources.append(resource)
            return resource
        capture = RecoveringAudio(factory, retry_min=.01, retry_max=.02)
        original = capture.buffer
        try:
            self.assertTrue(until(lambda: len(original.data) > 0))
            self.assertAlmostEqual(float(original.pull(10)[0, 0]), .25)
            resources[-1].error = 'signal lost'
            self.assertTrue(until(lambda: len(resources) >= 2))
            self.assertIs(capture.buffer, original)
        finally:
            capture.close()
        self.assertFalse(capture.worker.is_alive())
        self.assertTrue(all(resource.closed for resource in resources))
