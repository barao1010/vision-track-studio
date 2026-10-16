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

1. Camera capture, device selection, disconnect recovery and output threading.
   The default WASAPI microphone is now wired through the rate converter, mixer
   and recorder; validate physical devices and long-duration synchronization.
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

## Microphone integration increment

Added a Windows WASAPI worker for the default mono/stereo capture endpoint. It
requests float PCM at the device mix rate, uses the independent sinc converter
for 48 kHz output, duplicates mono into stereo, and timestamps a bounded history
using WASAPI QPC timestamps mapped to the application's monotonic clock. Capture
must be explicitly selected in the engineering window. Device loss, discontinuity,
missing timestamps and timeouts fail visibly; no automatic device substitution.
Mixer gain (-60 to +12 dB), mute and the output peak meter are connected to recording. A separate synthetic GUI
fixture tests the signal path and mute without claiming a physical microphone test.
Physical microphones, device switching, clock drift correction and long-running
A/V synchronization remain unvalidated. The recording path still waits on audio
on the UI thread; moving output off that thread remains necessary.

Commit `7167d44` passed Windows/Linux/comparison run 38937548432: eight Windows
contracts, decoded native tone fixture, silent GUI fixture (29 frames), and
synthetic GUI audio/mute fixture (85 frames). No physical capture endpoint was
opened by the GUI fixtures. The microphone code compiled; these results do not
prove hardware operation. The follow-up gain test checks +6 dB in decoded AAC.

Commit `7d52ba8` passed all jobs in run 38937789984, including decoded +6 dB
signal amplitude and mute in the GUI recording. Keep the fixed thresholds in
`validation/check_gui_recording.py`; this is not a physical-device test.
