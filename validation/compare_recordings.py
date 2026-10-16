"""Black-box comparison of the shared color/image/fade/audio fixture only.

FFmpeg is an external test decoder, not linked or bundled with the core.
The OBS reference contains a later browser scene, outside this test's scope.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np


def decode(path, args):
    return subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), *args, '-'],
                          check=True, capture_output=True, timeout=60).stdout


def measure(path):
    metadata = json.loads(subprocess.run(
        ['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(path)],
        check=True, capture_output=True, timeout=30).stdout)
    v = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
    a = next(s for s in metadata['streams'] if s['codec_type'] == 'audio')
    if (v['width'], v['height'], v['r_frame_rate'], a['sample_rate'], a['channels']) != (640, 360, '30/1', '48000', 2):
        raise ValueError('Expected 640x360 at 30fps and stereo 48kHz')
    raw = decode(path, ['-t', '7', '-map', '0:v:0', '-pix_fmt', 'rgb24', '-f', 'rawvideo'])
    pixels = np.frombuffer(raw, np.uint8).reshape(-1, 360, 640, 3)
    if len(pixels) < 205:
        raise ValueError('Video shorter than shared seven-second fixture')
    colors = np.median(pixels[:, 100:260:16, 100:540:16], axis=(1, 2))
    first = np.median(colors[30:75], axis=0)
    second = np.median(colors[150:195], axis=0)
    distance = np.linalg.norm(second-first)
    if distance < 100:
        raise ValueError('Missing distinct image scene')
    progress = ((colors-first) @ (second-first))/(distance**2)
    transition = np.flatnonzero((progress > .05) & (progress < .95))
    if not 5 <= len(transition) <= 12:
        raise ValueError(f'Fade must have intermediate frames, got {len(transition)}')
    if np.any(np.diff(progress[95:125]) < -.025):
        raise ValueError('Fade reverses direction')
    audio = np.frombuffer(decode(path, ['-t', '7', '-map', '0:a:0', '-f', 'f32le']), '<f4').reshape(-1, 2)
    if len(audio) < 6.9*48000 or not np.isfinite(audio).all():
        raise ValueError('Invalid or incomplete audio')
    stable = audio[48000:6*48000].astype(float)
    rms = np.sqrt(np.mean(stable**2, axis=0))
    if np.min(rms) < .05:
        raise ValueError('Silent/weak audio')
    spectrum = abs(np.fft.rfft(stable[:, 0]*np.hanning(len(stable))))
    hz = np.fft.rfftfreq(len(stable), 1/48000)[int(np.argmax(spectrum))]
    if abs(hz-440) > 2:
        raise ValueError('Wrong audio tone')
    return {'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'first_rgb': first.tolist(), 'second_rgb': second.tolist(),
            'fade_frames': int(len(transition)), 'fade_start': int(transition[0]),
            'rms': rms.tolist(), 'tone_hz': float(hz), 'decoded_frames': len(pixels)}


def compare(reference, candidate):
    errors = []
    for key in ('first_rgb', 'second_rgb'):
        if np.max(np.abs(np.array(reference[key])-candidate[key])) > 5:
            errors.append(f'{key}: difference exceeds 5/255 per channel')
    if abs(reference['fade_frames']-candidate['fade_frames']) > 2:
        errors.append('Fade length differs by more than two frames')
    if abs(reference['fade_start']-candidate['fade_start']) > 3:
        errors.append('Fade starts more than three frames apart')
    if np.max(abs(np.array(reference['rms'])/candidate['rms']-1)) > .05:
        errors.append('Channel RMS differs by more than 5 percent')
    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    ref, candidate = measure(args.reference), measure(args.candidate)
    errors = compare(ref, candidate)
    report = {'scope': 'color/image endpoints, fade timing, stereo tone/gain only',
              'not_validated': ['browser/CSS', 'live capture', 'streaming', 'UI', 'full OBS parity'],
              'reference': ref, 'candidate': candidate, 'errors': errors, 'passed': not errors}
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(errors))
