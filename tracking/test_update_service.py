# SPDX-License-Identifier: GPL-2.0-or-later
import hashlib
import io
from pathlib import Path
import shutil
import unittest
from update_service import select_release,valid_asset,download,ASSET


class UpdateValidationTests(unittest.TestCase):
    def release(self,tag='v0.1.0-preview.99'):
        return {'tag_name':tag,'draft':False,'assets':[{'name':ASSET,'digest':'sha256:'+'a'*64,'size':10,
                'browser_download_url':f'https://github.com/barao1010/vision-track-studio/releases/download/{tag}/{ASSET}'}]}

    def test_independent_engine_and_older_build_are_not_offered(self):
        self.assertIsNone(select_release([self.release('v0.2.0-dev.3')],1))
        self.assertIsNone(select_release([self.release()],99))
        self.assertEqual(select_release([self.release()],98)['build'],99)

    def test_missing_digest_and_draft_are_rejected(self):
        release=self.release();release['assets'][0]['digest']=None
        self.assertIsNone(select_release([release],1))
        release=self.release();release['draft']=True
        self.assertIsNone(select_release([release],1))

    def test_external_repository_and_insecure_urls_rejected(self):
        url=self.release()['assets'][0]['browser_download_url']
        self.assertFalse(valid_asset(url.replace('https:','http:'),'sha256:'+'a'*64))
        self.assertFalse(valid_asset(url.replace('barao1010','attacker'),'sha256:'+'a'*64))

    def test_download_requires_matching_bytes(self):
        url=self.release()['assets'][0]['browser_download_url']
        payload=b'fixture installer bytes'
        digest='sha256:'+hashlib.sha256(payload).hexdigest()
        result=download(url,digest,opener=lambda url:io.BytesIO(payload))
        path=Path(result['installer'])
        try: self.assertEqual(path.read_bytes(),payload)
        finally: shutil.rmtree(path.parent)
        with self.assertRaisesRegex(ValueError,'checksum'): download(url,'sha256:'+'a'*64,opener=lambda url:io.BytesIO(payload))
