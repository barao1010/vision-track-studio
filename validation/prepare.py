# SPDX-License-Identifier: GPL-2.0-or-later
"""Prepare an isolated portable profile; never touches user configuration."""
import argparse
import json
import math
from pathlib import Path
import struct
import wave
import uuid
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
def source(kind, name, settings):
    return {'id':kind.split('_v')[0], 'versioned_id':kind, 'name':name,
            'uuid':str(uuid.uuid5(uuid.NAMESPACE_URL, 'vision-parity/'+name)),
            'settings':settings, 'mixers':1, 'volume':0.8 if name=='Parity Audio' else 1.0}

inputs = [
    source('color_source_v3','Parity Color',{'width':640,'height':360,'color':4281558732}),
    source('image_source','Parity Image',{'file':(fixture/'image.png').as_posix()}),
    source('browser_source','Parity Browser',{'is_local_file':True,'local_file':(fixture/'browser.html').as_posix(),'width':640,'height':360,'css':'body { margin:0; overflow:hidden; }'}),
    source('ffmpeg_source','Parity Audio',{'local_file':(fixture/'tone.wav').as_posix(),'is_local_file':True,'looping':True})
]
scene_sources=[]
for index, visual in enumerate(inputs[:3],1):
    items=[{'name':item['name'],'source_uuid':item['uuid'],'id':i,'visible':True,'scale':{'x':1.0,'y':1.0},'pos':{'x':0.0,'y':0.0},'align':5} for i,item in enumerate([visual,inputs[3]],1)]
    scene_sources.append(source('scene',f'Parity {index}',{'items':items}))
(scenes/'Parity.json').write_text(json.dumps({
    'name':'Parity', 'current_scene':'Parity 1','current_program_scene':'Parity 1',
    'current_transition':'Fade','transition_duration':300,
    'sources':inputs+scene_sources,
    'scene_order':[{'name':s['name']} for s in scene_sources],
    'modules':{'scripts-tool':[{'path':(fixture/'parity.lua').as_posix(),'settings':{}}]}
}))
