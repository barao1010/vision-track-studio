"""Render and compare independent output against pinned OBS recordings."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from compare_recordings import measure, compare

EXPECTED = {
    'normal': 'b3b8695ac374c03359342d12891ae5a0c958cadc647542d6be2f6b2a3d918ba1',
    'studio': 'e1843cd426312dc28500dc69838bc7760b19bc1fc970697258a9eedb5cc3176d',
}


def run(renderer, reference, output):
    output.mkdir(parents=True, exist_ok=False)
    for name, rgb in [('color', (204, 102, 51)), ('image', (20, 200, 50))]:
        (output / f'{name}.ppm').write_bytes(b'P6\n640 360\n255\n'+bytes(rgb)*640*360)
    subprocess.run([str(renderer.resolve()), str(output/'color.ppm'), str(output/'image.ppm'),
                    str(output/'raw')], check=True, timeout=120)
    movie = output/'independent.mkv'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                    '-video_size', '640x360', '-framerate', '30', '-i', str(output/'raw/video.rgb'),
                    '-f', 'f32le', '-ar', '48000', '-ac', '2', '-i', str(output/'raw/audio.f32le'),
                    '-c:v', 'ffv1', '-c:a', 'pcm_f32le', str(movie)], check=True, timeout=120)
    candidate = measure(movie)
    report = {'scope': '7s file rendering: scene colors, image, fade timing, stereo tone/gain',
              'reference_run': 38859179964, 'reference_artifact': 12028698711,
              'obs_revision': 'f082210c177a03572cace88c168d0f32d8cde39e',
              'full_obs_parity': False, 'candidate': candidate, 'comparisons': {}}
    failures = []
    for mode, digest in EXPECTED.items():
        matches = list(reference.rglob(f'{mode}/recordings/exercise.mkv'))
        if len(matches) != 1:
            raise ValueError(f'Need exactly one {mode} reference recording')
        if hashlib.sha256(matches[0].read_bytes()).hexdigest() != digest:
            raise ValueError('Reference recording hash mismatch')
        metrics = measure(matches[0])
        errors = compare(metrics, candidate)
        report['comparisons'][mode] = {'reference': metrics, 'errors': errors, 'passed': not errors}
        failures.extend(errors)
    # Actual decoded negative controls: silence and a hard cut must fail measurement.
    for label, options in [
        ('silence', ['-af', 'volume=0']),
        ('cut', ['-vf', "select='lt(t,3.5)+gte(t,3.8)',setpts=N/(30*TB),tpad=stop_mode=clone:stop_duration=0.3"]),
    ]:
        broken = output/f'negative-{label}.mkv'
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(movie), *options,
                        '-c:v', 'ffv1', '-c:a', 'pcm_f32le', str(broken)], check=True, timeout=120)
        try:
            measure(broken)
        except ValueError:
            continue
        raise AssertionError(f'Negative control {label} incorrectly passed')
    report['negative_controls'] = ['silence rejected', 'hard cut rejected']
    report['passed'] = not failures
    (output/'comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'passed': not failures, 'errors': failures, 'full_obs_parity': False}))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('renderer', type=Path)
    p.add_argument('reference', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    run(args.renderer, args.reference, args.output)
