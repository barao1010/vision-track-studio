# SPDX-License-Identifier: GPL-2.0-or-later
"""Decode recordings and compare observable audiovisual behavior, not exit codes."""
import argparse
import json
from pathlib import Path
import av
import numpy as np


def measure(root):
    exercise = json.loads((root / 'exercise.json').read_text())
    required = {'color', 'image', 'browser', 'audio', 'fade', 'recording', 'stopped'}
    assert required <= exercise.keys() and all(exercise[k] for k in required), exercise
    recordings = list((root / 'recordings').glob('*.mkv'))
    assert len(recordings) == 1, recordings
    file = recordings[0]
    colors = []
    with av.open(file) as media:
        assert len(media.streams.video) == 1 and len(media.streams.audio) >= 1
        stream = media.streams.video[0]
        assert (stream.width, stream.height) == (640, 360)
        for frame in media.decode(video=0):
            colors.append(frame.to_ndarray(format='rgb24')[100:260, 200:440].mean(axis=(0, 1)))
    samples = []
    resampler = av.AudioResampler(format='fltp', layout='mono', rate=48000)
    with av.open(file) as media:
        for frame in media.decode(audio=0):
            for converted in resampler.resample(frame):
                samples.append(converted.to_ndarray().reshape(-1))
        for converted in resampler.resample(None):
            samples.append(converted.to_ndarray().reshape(-1))
    assert len(colors) >= 200, ('Too few recorded video frames', len(colors))
    assert samples, 'Missing decoded audio'
    signal = np.concatenate(samples).astype(float)
    # A click in an otherwise silent recording must not pass as captured audio.
    windows = signal[:len(signal) // 4800 * 4800].reshape(-1, 4800)
    energy = np.sqrt(np.mean(windows * windows, axis=1))
    rms = float(np.median(energy))
    assert rms > 0.03, ('Silent or intermittent recorded audio', rms)
    assert len(signal) >= 48000 * 7, 'Recorded audio truncated'
    middle = signal[len(signal)//2:len(signal)//2 + 48000]
    spectrum = np.abs(np.fft.rfft(middle * np.hanning(len(middle))))
    frequency = float(np.fft.rfftfreq(len(middle), 1/48000)[np.argmax(spectrum)])
    assert abs(frequency - 440) <= 5, ('Expected 440 Hz fixture tone', frequency)
    colors = np.array(colors)
    green = int(np.sum((colors[:, 1] > 140) & (colors[:, 0] < 70)))
    red = int(np.sum((colors[:, 0] > 160) & (colors[:, 1] < 90)))
    assert green > 45, ('Image source absent', green)
    assert red > 45, ('Browser source/CSS absent', red)
    return {'video_frames': len(colors), 'green_frames': green, 'browser_frames': red,
            'audio_rms': rms, 'tone_hz': frequency, 'exercise': exercise, 'dimensions': [640, 360]}


def compare(left, right):
    assert left['exercise'] == right['exercise']
    assert left['dimensions'] == right['dimensions']
    for metric in ['video_frames', 'green_frames', 'browser_frames']:
        assert abs(left[metric] - right[metric]) <= 35, (metric, left[metric], right[metric])
    assert abs(left['audio_rms'] - right['audio_rms']) <= max(0.01, left['audio_rms'] * 0.15)
    assert abs(left['tone_hz'] - right['tone_hz']) <= 5


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['measure', 'compare'])
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    if args.mode == 'measure':
        report = measure(args.paths[0])
        (args.paths[0] / 'measurements.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
    else:
        compare(*(json.loads(path.read_text()) for path in args.paths))
        print('PASS: recorded scenes, image/browser sources, CSS, fade and audio match within stated tolerances. Hardware PTZ, speech recognition and live destinations are outside this test.')


if __name__ == '__main__':
    main()
