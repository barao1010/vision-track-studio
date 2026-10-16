# SPDX-License-Identifier: GPL-2.0-or-later
"""Prepare an isolated portable profile; never touches user configuration."""
import argparse
import json
import math
from pathlib import Path
import struct
import wave
from PIL import Image

p = argparse.ArgumentParser()
p.add_argument('runtime', type=Path)
p.add_argument('flavor', choices=['upstream', 'vision'])
a = p.parse_args()
fixture = Path(__file__).resolve().parent
output = fixture / 'recordings'
output.mkdir(exist_ok=True)
with wave.open(str(fixture / 'tone.wav'), 'wb') as wav:
    wav.setnchannels(2)
    wav.setsampwidth(2)
    wav.setframerate(48000)
    wav.writeframes(b''.join(struct.pack('<hh', *([int(8000 * math.sin(2*math.pi*440*i/48000))]*2)) for i in range(48000*4)))
Image.new('RGB', (640, 360), (20, 200, 50)).save(fixture / 'image.png')
(fixture / 'browser.html').write_text('<html><body style="background:rgb(220,40,50);width:640px;height:360px"><div style="width:80px;height:80px;background:white"></div></body></html>')
config = a.runtime / 'config' / ('obs-studio' if a.flavor == 'upstream' else 'vision-track-studio')
profile = config / 'basic/profiles/Parity'
profile.mkdir(parents=True, exist_ok=True)
user = '[General]\nFirstRun=true\n[Basic]\nProfile=Parity\nProfileDir=Parity\nSceneCollection=Parity\nSceneCollectionFile=Parity\n[BasicWindow]\nPreviewProgramMode=false\n'
(config / 'user.ini').write_text(user)
(config / 'global.ini').write_text('[General]\nFirstRun=true\n')
(profile / 'basic.ini').write_text(f'''[General]
Name=Parity
[Video]
BaseCX=640
BaseCY=360
OutputCX=640
OutputCY=360
FPSType=0
FPSCommon=30
[Output]
Mode=Simple
[SimpleOutput]
FilePath={output.as_posix()}
RecFormat2=mkv
RecEncoder=x264
StreamEncoder=x264
RecQuality=Small
VBitrate=1200
ABitrate=128
[Audio]
SampleRate=48000
ChannelSetup=Stereo
''')
scenes = config / 'basic/scenes'
scenes.mkdir(parents=True, exist_ok=True)
(scenes / 'Parity.json').write_text(json.dumps({'name':'Parity', 'sources':[], 'scene_order':[], 'modules':{'scripts-tool':[{'path':(fixture/'parity.lua').as_posix(),'settings':{}}]}}))
