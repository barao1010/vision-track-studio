# SPDX-License-Identifier: GPL-2.0-or-later
"""Decode actual recordings, reject silence/blank output and compare both builds."""
import argparse
import json
from pathlib import Path
import av
import numpy as np

p=argparse.ArgumentParser()
p.add_argument('mode', choices=['measure','compare'])
p.add_argument('paths', nargs='+', type=Path)
a=p.parse_args()
if a.mode == 'measure':
    root=a.paths[0]
    exercise=json.loads((root/'exercise.json').read_text())
    required={'color','image','browser','audio','fade','recording','stopped'}
    assert required <= exercise.keys() and all(exercise[k] for k in required), exercise
    recordings=list((root/'recordings').glob('*.mkv'))
    assert len(recordings)==1, recordings
    file=recordings[0]
    colors=[]
    with av.open(file) as media:
        assert len(media.streams.video)==1 and len(media.streams.audio)>=1
        stream=media.streams.video[0]
        assert (stream.width,stream.height)==(640,360)
        for frame in media.decode(video=0):
            colors.append(frame.to_ndarray(format='rgb24')[100:260,200:440].mean(axis=(0,1)).tolist())
    energy=[]
    with av.open(file) as media:
        for frame in media.decode(audio=0):
            signal=frame.to_ndarray().astype(float)
            energy.append(float(np.sqrt(np.mean(signal*signal))))
    assert len(colors)>=200, len(colors)
    assert energy and max(energy)>0.01, 'Silent recorded audio'
    colors=np.array(colors)
    green=int(np.sum((colors[:,1]>140)&(colors[:,0]<70)))
    red=int(np.sum((colors[:,0]>160)&(colors[:,1]<90)))
    assert green>45, ('Image source absent',green)
    assert red>45, ('Browser source/CSS absent',red)
    report={'video_frames':len(colors),'green_frames':green,'browser_frames':red,'audio_rms':float(np.median(energy)), 'exercise':exercise,'dimensions':[640,360]}
    (root/'measurements.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
else:
    left,right=[json.loads(path.read_text()) for path in a.paths]
    assert left['exercise']==right['exercise']
    assert left['dimensions']==right['dimensions']
    for metric in ['video_frames','green_frames','browser_frames']:
        assert abs(left[metric]-right[metric]) <= 35, (metric,left[metric],right[metric])
    assert abs(left['audio_rms']-right['audio_rms']) <= max(0.01,left['audio_rms']*0.15)
    print('PASS: native recording, image/browser sources, CSS, scene changes, fade and recorded audio match within stated tolerances. Hardware PTZ, speech recognition and live destinations are outside this test.')
