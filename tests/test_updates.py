import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from io import BytesIO
from vtrack.updates import Updater, API


class UpdateTests(unittest.TestCase):
    def release(self, tag='independent-v1.0.0', prerelease=False):
        return {'tag_name': tag, 'prerelease': prerelease, 'draft': False, 'html_url': 'https://github.com/release', 'assets': [
            {'name': 'Vision-Track-Studio-1.0.0-Setup.exe', 'url': API + '/releases/assets/1'},
            {'name': 'SHA256SUMS.txt', 'url': API + '/releases/assets/2'}]}

    def test_old_previews_and_experimental_releases_never_offered(self):
        releases = [self.release('v0.1.0-preview.50'), self.release(prerelease=True)]
        updater = Updater('0.2.0-dev.2', fetch=lambda *args, **kwargs: json.dumps(releases).encode())
        self.assertIsNone(updater.check())

    def test_independent_final_requires_installer_and_checksum(self):
        releases = [self.release()]
        checksum = hashlib.sha256(b'installer').hexdigest()
        def fetch(url, **kwargs):
            return (checksum + '  Vision-Track-Studio-1.0.0-Setup.exe\n').encode() if '/assets/' in url else json.dumps(releases).encode()
        updater = Updater('0.2.0-dev.2', fetch=fetch)
        update = updater.check()
        self.assertEqual(update.version, '1.0.0')
        self.assertEqual(update.sha256, checksum)
        self.assertIsNone(Updater('1.0.0', fetch=fetch).check())
        releases[0]['assets'].pop()
        self.assertIsNone(updater.check())

    def test_checksum_failure_does_not_leave_executable(self):
        checksum = hashlib.sha256(b'expected').hexdigest()
        def fetch(url, **kwargs):
            return (checksum + '  Vision-Track-Studio-1.0.0-Setup.exe\n').encode() if '/assets/' in url else json.dumps([self.release()]).encode()
        updater = Updater('0.2.0-dev.2', fetch=fetch)
        update = updater.check()
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(updater.opener, 'open', return_value=BytesIO(b'bad-data')):
                with self.assertRaises(ValueError):
                    updater.download(update, folder)
            self.assertEqual(list(Path(folder).iterdir()), [])
