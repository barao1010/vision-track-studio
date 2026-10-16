# SPDX-License-Identifier: GPL-2.0-or-later
"""Prove real silence, absent sources and damaged audio cannot pass validation."""
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
import av
import numpy as np
from measure import measure


class RecordingValidation(unittest.TestCase):
    def make_recording(self, root, frequency=440, silence=False, browser=True):
        (root/'recordings').mkdir()
        (root/'exercise.json').write_text(json.dumps({k: True for k in ['color','image','browser','audio','fade','recording','stopped']}))
        with av.open(str(root/'recordings/test.mkv'), 'w') as mux:
            video = mux.add_stream('ffv1', rate=30)
            video.width, video.height = 640, 360
            video.pix_fmt = 'yuv420p'
            audio = mux.add_stream('pcm_s16le', rate=48000)
            audio.layout = 'stereo'
            for i in range(270):
                color = (30, 50, 180) if i < 90 else (20, 200, 50) if i < 180 else (220, 40, 50) if browser else (0,0,0)
                pixels = np.full((360,640,3), color, dtype=np.uint8)
                frame = av.VideoFrame.from_ndarray(pixels, format='rgb24')
                frame.pts, frame.time_base = i, Fraction(1,30)
                for packet in video.encode(frame): mux.mux(packet)
            for packet in video.encode(): mux.mux(packet)
            for i in range(0,48000*9,4800):
                data = np.zeros(4800) if silence else .18*np.sin(2*np.pi*frequency*np.arange(i,i+4800)/48000)
                stereo = np.repeat((data*32767).astype(np.int16),2).reshape(1,-1)
                frame = av.AudioFrame.from_ndarray(stereo,format='s16',layout='stereo')
                frame.sample_rate = 48000
                frame.pts, frame.time_base = i, Fraction(1,48000)
                for packet in audio.encode(frame): mux.mux(packet)
            for packet in audio.encode(): mux.mux(packet)

    def test_valid_recording(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.make_recording(root)
            self.assertAlmostEqual(measure(root)['tone_hz'],440,delta=1)

    def test_silence_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.make_recording(root,silence=True)
            with self.assertRaisesRegex(AssertionError,'Silent'): measure(root)

    def test_wrong_audio_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.make_recording(root,frequency=880)
            with self.assertRaisesRegex(AssertionError,'440 Hz'): measure(root)

    def test_blank_browser_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.make_recording(root,browser=False)
            with self.assertRaisesRegex(AssertionError,'Browser source'): measure(root)
