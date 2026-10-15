import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from PIL import Image
from vtrack.media import VideoOutput, Decoder


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg/ffprobe necessários')
class MediaTests(unittest.TestCase):
    def test_actual_encode_decode(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'record.mkv'
            output = VideoOutput(str(path), (64, 48), 10)
            for _ in range(10):
                output.submit(Image.new('RGB', (64, 48), 'red'))
                time.sleep(.03)
            output.close()
            probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))
            stream = probe['streams'][0]
            self.assertEqual((stream['width'], stream['height']), (64, 48))
            self.assertGreater(float(probe['format']['duration']), .1)
            decoder = Decoder(str(path), (64, 48))
            try:
                deadline = time.monotonic() + 5
                while decoder.frame() is None and time.monotonic() < deadline:
                    time.sleep(.05)
                frame = decoder.frame()
                self.assertIsNotNone(frame)
                red, green, blue = frame.getpixel((10, 10))
                self.assertGreater(red, 230)
                self.assertLess(green + blue, 30)
            finally:
                decoder.close()
            with self.assertRaises(FileExistsError):
                VideoOutput(str(path), (64, 48), 10)

    def test_encoder_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            output = VideoOutput(str(Path(folder) / 'absent' / 'bad.mkv'), (64, 48), 10)
            output.submit(Image.new('RGB', (64, 48)))
            with self.assertRaises(RuntimeError):
                output.close()


if __name__ == '__main__':
    unittest.main()
