# SPDX-License-Identifier: GPL-2.0-or-later
"""Fetch the Apache-2.0 Portuguese Vosk model from its official distribution."""
import hashlib
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

EXPECTED='6e1ce909032e1afa7a88e68a3d628ecafff302bdf195befab308826c395e93b7'
URL='https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip'
destination=Path(__file__).resolve().parent.parent/'tracking/models/speech-model'
with tempfile.TemporaryDirectory() as tmp:
    archive=Path(tmp)/'model.zip'
    urllib.request.urlretrieve(URL,archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=EXPECTED:
        raise RuntimeError('Speech model checksum mismatch')
    with zipfile.ZipFile(archive) as files:
        if sum(f.file_size for f in files.infolist())>150*1024*1024:
            raise RuntimeError('Speech model exceeds expected size')
        base=Path(tmp)/'unpacked'
        for item in files.infolist():
            target=(base/item.filename).resolve()
            if not target.is_relative_to(base.resolve()): raise RuntimeError('Unsafe archive path')
        files.extractall(base)
    source=base/'vosk-model-small-pt-0.3'
    if not (source/'final.mdl').is_file(): raise RuntimeError('Speech model is incomplete')
    shutil.copytree(source,destination,dirs_exist_ok=True)
print('Verified Portuguese speech model.')
