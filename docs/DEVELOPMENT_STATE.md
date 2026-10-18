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


## Output worker increment — 2026-10-17

Audio waits, mixing and MP4 encoding now run in a bounded eight-packet worker
queue. Frames are immutable shared snapshots; gain and mute are captured with
each frame. Factory creation, COM/MF lifetime, writes, finalization and resource
destruction stay on the worker. Queue saturation fails explicitly instead of
blocking the producer or growing memory indefinitely. Starting still waits for
initialization and stopping drains/finalizes synchronously; those two operations
can still briefly block the window. Composition/capture remain on the UI thread.
Deterministic tests block the sink while submitting and exercise queue limits,
FIFO drain, thread affinity, initialization/write failure and repeated finish.
Local warning-clean and ASan+UBSan checks passed (detect_leaks=0). Windows decode
regressions must pass before this increment is considered validated.
The user's 16/10 clarification rejects a partial testing delivery: do not package
or deliver the engineering shell in place of the requested complete application.

Validation completed for `a2f6f16` in run 39072542555: Windows, Linux and
recorded comparison all passed. Windows also decoded the native and GUI MP4
fixtures with unchanged video, timestamp, +6 dB tone and mute criteria.
The output worker tests also passed locally with ASan+UBSan (leaks disabled).
This establishes the output-worker increment, not physical-device validation,
full interface responsiveness under load, or complete OBS parity.

## Project persistence increment — 2026-10-17

Added an original versioned .vts project format for source identity, ordered scenes
and layers, image paths, desktop/solid sources, crop/position/opacity/visibility,
preview/program selection and microphone/gain/mute settings. Save validates first
and replaces via a same-filesystem temporary file; malformed/oversized versions,
duplicate IDs and dangling sources are rejected. This is not a power-loss
durability guarantee. Image paths are resolved against the project directory.
The engineering window now has save/open actions. Open prepares and validates
all sources/scenes before replacing the active project; missing images or invalid
crops leave the current state intact. Loading while recording is rejected.
An in-progress fade is saved as its target scene, not as a transition snapshot.

Local project contracts passed warning-clean and ASan+UBSan (detect_leaks=0).
GUI contracts now exercise save, remove, reopen, compare restored settings and
blue program pixels, and preserve state on invalid-file failure. Windows CI
validation is pending for this increment. The window remains an engineering
harness, and no partial delivery is authorized. Device capture, browser, final
interface, streaming and the other missing features still require implementation.

Persistence validation: d1b429d passed all jobs in run 39076646915; 10 Windows
contracts, native 90-frame decode, silent GUI 27 frames, tone/mute GUI 84 frames.
This includes GUI save/reopen/state-preservation checks, not hardware validation.

## Transform editing increment — 2026-10-18

Added transactional Scene::transform validation and connected position, dimensions,
four crop edges and opacity percent to engineering-window controls. Layer up/down
changes both the compositor order and serialized order. Selection remains on the
moved item. Removing the last reference to a source releases its descriptor's
strong reference rather than retaining every removed image until project close.
Core pixel tests cover crop/position/opacity and reject invalid edits even on
hidden layers without changing their prior state; local warning-clean and
ASan+UBSan passed (detect_leaks=0). GUI tests now apply a half-width transparent
layer, check pixels, reorder against a red background, and save/reopen that order.
Windows CI remains pending for this increment. No final interface or installer
has been delivered. Next work remains camera/device lifecycle, browser sources,
scheduler, streaming and approved interface, followed by extras and packaging.

Historical run 39072728460 (docs-only commit a1eae10) failed its desktop pixel
fixture while other contracts passed. The fixture flushed GDI without waiting
for desktop presentation. Added an explicit DwmFlush presentation fence (no
pixel-threshold reduction or retry-until-pass), and alternate red/green across
all five captures to detect stale frames. This addresses the observed setup race
hypothesis; Windows CI must validate the change.

Run 39090876240 passed Linux/comparison but GUI checks failed: the new overlap
check sampled x=500, outside the aspect-fitted 360px square background's [140,500)
bounds. Corrected the fixture sample to x=400, inside both layers. The expected
opaque red and 50/50 red-blue values are unchanged. This is a test-coordinate
correction; it does not establish a passing Windows run yet.

Validation complete for 848aada: run 39091002519 passed Windows, Linux and
recorded-comparison. Windows passed all 10 contracts, including GUI transform,
layer-order and project-restore checks and alternating desktop colors. Decodes
passed unchanged criteria: native90 frames, silentGUI29, tone/muteGUI84.
This is incremental validation; all remaining feature/delivery limitations above
still apply. Next work should implement camera/device capture or browser sources,
not repackage this engineering window.

## Camera capture increment — 2026-10-18 (validation pending)

Original Windows Media Foundation asynchronous source-reader adapter added.
Enumerates names and persistent symbolic links; chooses a native mode near
640x360/30 within 1920x1080 CPU limits, requests RGB32, converts padded or negative
stride buffers into linear opaque pixels on MF callbacks. Only one read is pending
per source; UI reads the latest frame and never waits for a capture sample.
Startup/shutdown and manual reconnect still happen synchronously. Device failures,
format changes and 5-second stalls are explicit errors. Reconnect releases and
reopens only the selected symbolic link; it never substitutes a different camera.
The initial frame is transparent pending capture, not a fake feed.

Engineering controls refresh/select/add/reconnect camera sources. Multiple scene
items share an existing camera instance, including on project reopening, avoiding
a second acquisition of the device. Camera identity is persisted in .vts.
No physical device has been opened/tested here; CI tests real MF buffer conversion,
padding, bottom-up orientation, alpha, truncation/unlock and enumeration only.
Actual hardware, disconnect/reconnect behavior and long sessions need validation.

No additional library was integrated: Windows SDK/OS COM and MF APIs only.
References used for API contracts, not copied implementations:
https://learn.microsoft.com/en-us/windows/win32/api/mfobjects/nf-mfobjects-imf2dbuffer-lock2d
https://learn.microsoft.com/en-us/windows/win32/api/mfreadwrite/nn-mfreadwrite-imfsourcereadercallback
https://learn.microsoft.com/en-us/windows/win32/medfound/mf-source-reader-enable-video-processing

Camera frame selection currently uses the most recent sample, without device-clock
latency compensation. This is not evidence of long-duration camera/audio sync.
Added a real MF 2D-buffer test alongside contiguous buffers; no hardware required.
Camera project contracts passed local ASan+UBSan (detect_leaks=0).

Camera increment validation: a76ba92 passed all jobs in run39093151855.
Windows passed11 contracts including native contiguous and 2D buffers and device
enumeration; decode regressions passed native90, silentGUI28, tone/muteGUI84
frames with unchanged criteria. Earlier bc62dbd run39093079553 also passed.
These tests do not activate a physical camera or validate device reconnection.
Next implement browser/CSS sources or scheduler/approved interface integration;
streaming, extras and complete delivery remain outstanding.

## Independent output clock — 2026-10-18 (Windows validation pending)

ScheduledOutput now owns 30fps/48kHz recording deadlines on its sink worker. UI
updates replace a single immutable video/gain/mute snapshot; stalled repaint
holds the last picture while audio and encoder timestamps keep advancing. This
removes the UI catch-up loop and queue-full failures caused by delayed repaint.
An encoder more than10s behind fails explicitly. Factory, writes, finish and
destruction stay on one worker. Start waits for the first encoded frame and stop
waits for the in-flight write/finalization, so both still can block the UI.
Capture/composition, camera polling and transitions still run on the UI thread;
this is NOT a complete rendering scheduler or validation of physical A/V sync.

Tests block the encoder, replace1000 snapshots without enqueue/backpressure,
verify held frames without producer updates, contiguous frame/audio positions,
latest gain/mute, thread affinity, shutdown and initialization failure. Local
warning-clean and ASan+UBSan passed (detect_leaks=0). Windows decode regressions
must pass unchanged. Browser/CSS, approved interface, streaming and extras remain.

Output clock6b9acfe passed all jobs in run39096838929, including Windows decode
regressions. Added selectable recording24/25/30/50/60fps, fixed48kHz audio blocks
matched to each rate, and project format2 with backward reading of format1
(default30fps). The recording rate control is disabled during recording. Canvas
remains640x360 and UI composition remains approximately30Hz: 50/60fps output
can contain held pictures, not50/60 distinct captured images. Fractional frame
rates and full output profiles remain unimplemented.
Rate tests verify scheduled audio intervals for all5 rates. Native Windows output
fixtures now encode/decode3 seconds at each rate with the same orientation,
color, timestamp and audio criteria as the existing30fps test. Validation pending.

Rate validation completed:5311830 run39110294755 passed all3 jobs,16 Windows
contracts and real H264/AAC decodes of72/75/90/150/180 frames at24/25/30/50/60fps.
Orientation, audio tone level/frequency and timestamps retained the existing
thresholds. GUI silence29frames and tone/mute83frames also passed. Local rate
and project tests passed ASan+UBSan (detect_leaks=0). No hardware validation or
full OBS equivalence is implied. Next priority: browser/CSS and approved UI.

## Browser source increment — 2026-10-18 (Windows validation pending)

Original WebView2 adapter renders HTTP/HTTPS or inline test HTML, applies custom
CSS after navigation, and captures PNG through WIC into linear straight-alpha
frames. Capture is asynchronous and limited to10Hz with one outstanding request;
host is an offscreen window with a pumping STA loop. Transparent while loading;
initialization/capture errors are explicit. This is not a production60fps browser
compositor. Browser audio is explicitly muted, and audio routing remains pending.
Permissions and new windows are denied. Source URL/CSS and size are persisted in
project version3, retaining reads of versions1/2. Engineering controls add URL/CSS
sources; editing existing source settings is still pending.
Actual WebView2 pixel test uses inline HTML: CSS changes blue to red while empty
background must remain transparent. It must pass, not merely compile.

Dependency review: downloaded Microsoft.Web.WebView2 SDK1.0.3537.50 from NuGet;
LICENSE.txt permits source/binary redistribution with notice/disclaimer and no
endorsement. Preserved verbatim at licenses/WebView2-SDK.txt. CMake pins package
SHA256 5ea526bbd728adda0da4d31219267e96460494a427e4894c4e09d9f320f4b9aa.
Only SDK loader is linked; Edge WebView2 Runtime must be installed separately.
Runtime redistribution/installer and third-party notice packaging remain pending.
This does not import OBS or Streamlabs code. No final package is published.

Follow-up: force browser rasterization scale1 for deterministic source dimensions
and ignore stale CSS/capture callbacks after navigation changes. Script dialogs
are disabled so remote pages cannot block the source host. Project version3
roundtrip tests passed local ASan+UBSan with detect_leaks=0.

Browser c0c17f9 validated in run39115241344: all3 jobs passed,17 Windows
contracts including actual CSS/transparency pixels. Native recordings decoded
90/72/75/150/180frames and GUI28silent/86tone-mute with unchanged thresholds.
No browser audio, high-frame-rate browser performance or hardware parity implied.

Browser editing increment: selected source loads URL/CSS into fields; Apply CSS
replaces a dedicated style element on the existing page without creating another
browser instance. Reload reopens the same URL/test HTML and reapplies saved CSS.
Frames from before the operation are invalidated, including in-flight captures.
CSS size is checked before mutation; edits wait for navigation to complete.
Project snapshots retain edited CSS. Tests now require red-to-green CSS update,
transparent background, no stale frame immediately after edit/reload, and green
again after reload. Each of three phases retains25s deadline (overall test90s).
Windows validation pending. URL editing of existing sources remains pending;
current controls remain engineering UI, not the approved final interface.
