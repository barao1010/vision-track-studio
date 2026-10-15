import json
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from vtrack.audio import PCMBuffer, Mixer
from vtrack.output import AVOutput


class AudioTests(unittest.TestCase):
    def test_gain_mute_scene_gating_and_limiter(self):
        a, b = PCMBuffer(), PCMBuffer()
        mixer = Mixer()
        mixer.add('a', a)
        mixer.add('b', b)
        a.push(np.ones((100, 2)) * .6)
        b.push(np.ones((100, 2)) * .6)
        result = mixer.mix(100)
        self.assertTrue(np.all(result == 1))
        self.assertEqual(mixer.clipped, 200)
        self.assertAlmostEqual(mixer.channels['a'].peak, .6, places=5)
        a.push(np.ones((100, 2)))
        b.push(np.ones((100, 2)))
        mixer.channels['a'].muted = True
        mixer.channels['b'].active = False
        self.assertTrue(np.all(mixer.mix(100) == 0))
        self.assertEqual(len(b.data), 0)

    def test_bounded_buffer_and_silence_on_underflow(self):
        buffer = PCMBuffer(20)
        buffer.push(np.ones((100, 2)))
        self.assertEqual(buffer.overruns, 80)
        result = buffer.pull(40)
        self.assertTrue(np.all(result[20:] == 0))
        self.assertEqual(buffer.underruns, 20)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg necessário')
    def test_actual_audio_video_file_and_duration(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'av.mkv'
            output = AVOutput(str(path), (64, 48), 10)
            try:
                for _ in range(75):
                    output.submit(Image.new('RGB', (64, 48), 'red'))
                    t = np.arange(960) / 48000
                    signal = (.2 * np.sin(2 * np.pi * 440 * t)).astype('float32')
                    output.submit_audio(np.column_stack((signal, signal)))
                    time.sleep(.02)
            finally:
                output.close()
            data = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))
            self.assertEqual({stream['codec_type'] for stream in data['streams']}, {'audio', 'video'})
            self.assertGreater(float(data['format']['duration']), 1)
            self.assertLess(float(data['format']['duration']), 3)
            raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-vn', '-f', 'f32le', '-ac', '2', 'pipe:1'])
            self.assertGreater(float(np.max(np.abs(np.frombuffer(raw, dtype='<f4')))), .1)
