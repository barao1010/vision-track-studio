# Vision Track Studio — independent implementation

This branch starts a new implementation from functional requirements. It does not
contain or link the OBS/Streamlabs engine, frontend, assets, or copied algorithms.
The previous native OBS derivative is preserved on `fix/restore-native-obs` and
retains its existing licensing obligations. Git ancestry is retained for project
history, not included as source in this branch's build.

## Implemented here

- CPU linear-light RGBA composition, shared immutable source interface, scene
  item identities, layer ordering, visibility, opacity, position, scale and crop.
- Cut and timed fade, live source sampling during transitions, continuous visual
  interruption of an in-progress fade, monotonic nanosecond clock validation.
- Timestamp-aligned mono/stereo float audio mixing with gain, mute, hard clipping,
  peak/RMS measurement and silence filling. Inputs must already share sample rate.
- File-backed P6 image decoding and raw RGB/stereo float recording with strict
  timestamps, format checks and refusal to overwrite existing output.
- Executable pixel/sample contract tests. Standard C++20 library only; no bundled
  third-party runtime dependencies in this initial core.

## Build and test

```
cmake -S . -B build
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

## Incomplete — not an application release

A Windows engineering shell now exercises scene/image controls and preview/program
cut/fade. It is not the approved delivery UI. No hardware capture, browser/CSS engine, output encoding, streaming,
encoded recording, resampling, GPU composition, persistence, settings UI, plugin ABI,
installer, PTZ/AI integration or Bible integration has been implemented in this
branch yet. CPU reference composition uses nearest-neighbour scaling; it is not
performance-equivalent to OBS. Tests validate this core's explicit contracts,
not full OBS parity. Do not ship this as an OBS replacement.

Next: extend source lifecycle and scheduling, add file-backed fixtures and media
output adapters, then validate actual recordings before building the desktop UI.
Review each dependency's exact build and redistribution terms before integration.
No conclusion about licensing of a future complete app follows from core tests.

## Recorded comparison evidence

On 2026-10-16 the independently rendered seven-second sequence was compared
against actual OBS recordings from run 38859179964 (artifact 12028698711).
Reference files are SHA-256 pinned in `validation/run_comparison.py`. Both normal
and studio reference captures passed this LIMITED comparison: scene RGB endpoints
within 5/255, fade duration within two frames, start within three frames, stereo
RMS within 5%, 440 Hz tone within 2 Hz. Silence and a hard-cut negative control
were rejected. This does not test the independent UI or studio mode (neither
exists), browser sources, real-time capture or streaming.

Run with an extracted reference artifact and a fresh output directory:

```
python validation/run_comparison.py build/render_fixture REFERENCE_DIR build/comparison
```

The core writes raw RGB and float audio. An external FFmpeg TEST TOOL muxes and
decodes the comparison files; it is not bundled or linked into the product. The
test environment's FFmpeg may be GPL-enabled. This is not a choice of shipping
encoder dependency. Review dependencies before creating a distributable app.

UI requirement: reproduce the previously approved Vision Track interface, including
panel placement/colors/controls; app/windows.cpp is a temporary functional harness,
not an approved replacement design. Windows tests exercise its real command handler.

## Windows platform progress

`platform/windows_desktop.cpp` captures desktop pixels using Windows GDI and is
connected to the engineering shell's source list. The Windows contract test
creates a colored window and checks captured pixels. This is not webcam capture
or a substitute for testing protected content, multiple monitors, DPI or latency.

`platform/windows_recording.cpp` uses installed Media Foundation encoders for
H.264/AAC MP4 output. A three-second recording test decodes all 90 frames and
checks top/bottom orientation, timestamps, stereo audio duration, 440Hz frequency
and amplitude. The first run found vertical inversion; a row-order correction
is being validated. The recorder is not yet wired to the user-facing record
button, microphone or camera, and is not a complete streaming pipeline.

### Audio rate conversion

`AudioRateConverter` is original C++20 code with no third-party dependency. It
converts contiguous mono/stereo float PCM between 8–192 kHz using a 64-tap
windowed-sinc filter, a rational sample clock and 32 source frames of lookahead.
It preserves output timestamps across input packet boundaries, suppresses
out-of-band energy when downsampling, and flushes the final edge without adding
stream duration (the final output frame count rounds up). It does not implement
clock-drift correction, microphone capture or multichannel layout conversion.
Tests compare the output against an analytic 440 Hz waveform, verify 44.1→48 kHz
chunk invariance, stereo isolation, 48→16 kHz passband/alias rejection, identity,
short/empty streams and malformed packets. These are signal-processing contracts,
not evidence of live device synchronization or complete OBS equivalence.
