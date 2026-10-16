import shutil
import tempfile
import time
import unittest
import wave
from pathlib import Path
import numpy as np
from vtrack.engine import Source, Scene, Project, Studio
from vtrack.runtime import Runtime


@unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg necessário')
class RuntimeMediaTests(unittest.TestCase):
    def test_actual_audio_source_routes_meters_and_releases_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tone.wav'
            samples = (.2 * np.sin(np.arange(48000) * 2 * np.pi * 440 / 48000) * 32767).astype('<i2')
            with wave.open(str(path), 'wb') as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(48000)
                handle.writeframes(samples.tobytes())
            source = Source('Áudio', 'audio', str(path))
            studio = Studio(Project(scenes=[Scene('Programa', [source])]))
            runtime = Runtime()
            wrapper = None
            try:
                runtime.attach(source)
                wrapper = runtime.audio[source.id]
                runtime.update_audio(studio, time.monotonic())
                deadline = time.monotonic() + 6
                while runtime.mixer.channels[source.id].peak < .1 and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertGreater(runtime.mixer.channels[source.id].peak, .1)
            finally:
                runtime.close()
            self.assertFalse(wrapper.worker.is_alive())
            self.assertFalse(runtime.audio_worker.is_alive())
            path.unlink()
