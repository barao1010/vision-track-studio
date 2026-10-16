# SPDX-License-Identifier: GPL-2.0-or-later
"""Convert the publisher's public-domain BPM snapshot without altering verse text."""
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tracking'))
from bible_index import BOOKS, BibleIndex

URL='https://ebible.org/Scriptures/porbrbsl_vpl.zip'
EXPECTED='ac9010c981d2a6f91c9f2e170d07c5d92e9bc296588ea00645aa4b504670e701'
request=urllib.request.Request(URL,headers={'User-Agent':'VisionTrackStudio/1.0 (+https://github.com/barao1010/vision-track-studio)'})
blob=urllib.request.urlopen(request,timeout=120).read(16*1024*1024)
if hashlib.sha256(blob).hexdigest()!=EXPECTED: raise RuntimeError('Default Bible snapshot checksum mismatch')
archive=zipfile.ZipFile(io.BytesIO(blob))
standard='GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SOL ISA JER LAM EZE DAN HOS JOE AMO OBA JON MIC NAH HAB ZEP HAG ZEC MAL MAT MAR LUK JOH ACT ROM 1CO 2CO GAL EPH PHI COL 1TH 2TH 1TI 2TI TIT PHM HEB JAM 1PE 2PE 1JO 2JO 3JO JUD REV'.split()
extra='TOB JDT ESG WIS SIR BAR 1MA 2MA 1ES PRM PSX 3MA 4ES 4MA DNG'.split()
names=dict(zip(standard+extra,[book[0] for book in BOOKS]))
verses=[]
unavailable=[]
for line in archive.read('porbrbsl_vpl.txt').decode('utf-8-sig').splitlines():
    match=re.fullmatch(r'(\S+) (\d+):(\d+) (.*)',line)
    if not match: raise RuntimeError('Unrecognized verse line')
    code,chapter,verse,text=match.groups()
    if code not in names: raise RuntimeError('Unrecognized book code')
    if not text:
        unavailable.append({'book':names[code],'chapter':int(chapter),'verse':int(verse)})
        continue
    verses.append({'book':names[code],'chapter':int(chapter),'verse':int(verse),'text':text})
document={'translation':'Bíblia Portuguesa Mundial (BPM) — rascunho de 13/10/2026',
          'license':'Public Domain — https://ebible.org/porbrbsl/copyright.htm',
          'source':URL,'source_sha256':EXPECTED,'verses':verses,'unavailable_verses':unavailable}
index=BibleIndex(document)
if len(index.verses)!=38029 or len(unavailable)!=29 or len({v.book for v in index.verses.values()})!=81:
    raise RuntimeError('Default Bible corpus is incomplete')
destination=ROOT/'tracking/data'
destination.mkdir(exist_ok=True)
(destination/'BPM.json').write_text(json.dumps(document,ensure_ascii=False),encoding='utf-8')
(destination/'LICENSE-BPM.txt').write_text('Bíblia Portuguesa Mundial (BPM)\nPublic Domain\nPublisher: eBible.org\nSource snapshot dated 2026-10-13.\nThis is a draft translation still under revision, as stated by the publisher.\nhttps://ebible.org/porbrbsl/copyright.htm\n'+URL+'\nSHA-256 '+EXPECTED+'\n',encoding='utf-8')
print('Verified BPM public-domain snapshot: 81 books, 38029 verses with text; 29 empty publisher entries unavailable. Draft translation.')
