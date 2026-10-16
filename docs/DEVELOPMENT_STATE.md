# Independent implementation checkpoint — 2026-10-16

Active branch: `independent-core-v2`. Preserve the OBS derivative branch and PR #2
with their licensing obligations. This branch must not import OBS/Streamlabs
source, frontend or assets. Tests using separately generated OBS recordings do
not make OBS a product dependency.

## Verified increments

- `1b9b1bd`: Windows Media Foundation RGB32 row order fixed after the decoded
  recording exposed vertical inversion. Run 38934171835 passed all jobs.
- `b9e1432`: original streaming windowed-sinc audio converter, rational sample
  timestamps, packet-boundary invariance, 44.1→48 kHz analytic tone accuracy,
  48→16 kHz alias rejection, stereo and malformed-input contracts. Run
  38934795101 passed Windows, Linux and recorded-comparison jobs. Local
  ASan+UBSan passed with `ASAN_OPTIONS=detect_leaks=0`; leak detection is not
  supported by this container.
- `3d54197`: engineering window record button now writes native MP4 from its
  program output. Run 38935120740 passed all jobs. Windows ran six CTest
  contracts; the decoded encoder fixture had 90 correctly oriented H264 frames
  and stereo AAC 440 Hz audio. The separately decoded GUI recording had 28
  H264 frames, a red-to-blue fade, correct timestamps and an explicitly silent
  AAC track. The GUI action test sends start/stop through WM_COMMAND.
- The pinned seven-second OBS comparison remains limited to scene endpoint
  colors, fade timing and synthetic stereo tone. Negative silence/hard-cut
  controls must continue to fail. Do not weaken criteria or claim full parity.

## Next implementation work

1. Live microphone/camera adapters, device selection, disconnect recovery and
   threading. Route microphone PCM through the rate converter and mixer before
   recording. The GUI currently says "sem audio" because no microphone is wired.
2. Replace the engineering window with the approved interface. The approved
   reference is a dark 1536×1024 layout: scenes upper left, large preview beside
   it, smaller program/transition center-right, mixer and controls far right;
   sources lower left, PTZ cards/controls below preview, tracking and Bible below
   PTZ, stream settings bottom-right. Do not generate a new design or show fake
   live meters, fake device feeds or working controls for absent functionality.
3. Source lifecycle/scheduler, persistent scenes/profiles/settings, browser/CSS,
   video sources, RTMP output with local-only test receiver and failure handling.
4. PTZ target persistence, fixed-camera zoom, Bible voice and updater integration;
   user will perform hardware/extra-feature tests. Do not invent hardware results
   or Bible redistribution rights.
5. Installer and actual end-to-end validation before delivery. CPU rendering and
   synchronous GUI encoding are not a production scheduler or performance parity.

No installer or complete application is ready. No public streams were started.
The previous approved screenshot was inspected as a visual reference; it has
not been bundled into the app or used as fake functional UI.
