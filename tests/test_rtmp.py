import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest
import numpy as np
from PIL import Image
from vtrack.media import ffmpeg, spawn
from vtrack.output import AVOutput


@unittest.skipUnless(os.environ.get('VISION_TRACK_TEST_RTMP') == '1', 'Ative VISION_TRACK_TEST_RTMP=1 para servidor local')
class RTMPTests(unittest.TestCase):
    def test_actual_rtmp_publish_to_local_receiver(self):
        with socket.socket() as portfinder:
            portfinder.bind(('127.0.0.1', 0))
            port = portfinder.getsockname()[1]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'received.mkv'
            url = f'rtmp://127.0.0.1:{port}/live/test'
            receiver = spawn([ffmpeg(), '-nostdin', '-loglevel', 'error', '-listen', '1', '-i', url, '-c', 'copy', '-f', 'matroska', str(path)], stderr=subprocess.PIPE)
            output = None
            try:
                time.sleep(.5)
                output = AVOutput(url, (64, 48), 10, live=True)
                for _ in range(120):
                    output.submit(Image.new('RGB', (64, 48), 'blue'))
                    output.submit_audio(np.ones((960, 2), dtype='float32') * .1)
                    time.sleep(.02)
                output.close()
                output = None
                receiver.wait(timeout=8)
                data = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(path)]))
                self.assertEqual({stream['codec_type'] for stream in data['streams']}, {'audio', 'video'})
            finally:
                if output:
                    output.close()
                if receiver.poll() is None:
                    receiver.kill()
                    receiver.wait()
                receiver.stderr.close()
