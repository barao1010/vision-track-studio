"""Decode the MP4 produced by actual window actions; no device audio is claimed."""
import sys
import av
import numpy as np

path = sys.argv[1]
with av.open(path) as recording:
    stream = recording.streams.video[0]
    assert stream.codec_context.name == 'h264'
    frames = list(recording.decode(video=0))
assert 15 <= len(frames) <= 300, len(frames)
assert all((f.width, f.height) == (640, 360) for f in frames)
pts = np.array([float(f.pts * f.time_base) for f in frames])
assert np.allclose(np.diff(pts), 1 / 30, atol=1e-6), pts
rgb = np.array([f.to_ndarray(format='rgb24')[180, 320] for f in frames])
assert rgb[0, 0] > 230 and rgb[0, 2] < 20, rgb[0]
assert rgb[-1, 2] > 230 and rgb[-1, 0] < 20, rgb[-1]
assert np.any((rgb[:, 0] > 40) & (rgb[:, 2] > 40)), rgb
with av.open(path) as recording:
    stream = recording.streams.audio[0]
    assert stream.codec_context.name == 'aac'
    assert stream.codec_context.sample_rate == 48000
    assert stream.codec_context.channels == 2
    samples = np.concatenate([f.to_ndarray() for f in recording.decode(audio=0)], axis=1)
if '--tone' in sys.argv:
    active = samples[0, 4800:24000]
    assert abs(float(np.sqrt(np.mean(active**2))) - .2 * 10**(6 / 20) / np.sqrt(2)) < .01
    spectrum = np.abs(np.fft.rfft(active))
    frequency = np.fft.rfftfreq(len(active), 1 / 48000)[np.argmax(spectrum)]
    assert abs(frequency - 440) < 3, frequency
    assert np.max(np.abs(samples[:, -4800:])) < .001, 'Mute did not reach encoded audio'
else:
    assert np.max(np.abs(samples)) < 1e-6
assert abs(samples.shape[1] / 48000 - len(frames) / 30) < .05
print(f'PASS: GUI recording, {len(frames)} H264 frames, red-to-blue fade, timestamps, AAC tone/mute pipeline' if '--tone' in sys.argv else f'PASS: GUI recording, {len(frames)} H264 frames, red-to-blue fade, timestamps, silent AAC')
