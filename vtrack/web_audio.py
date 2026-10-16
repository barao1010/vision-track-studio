"""HTML5 media audio bridge. Respects Chromium origin/CORS restrictions."""
SCRIPT = r'''(() => {
  if (!window.AudioContext || !window.HTMLMediaElement) return;
  const context = new AudioContext({sampleRate: 48000});
  const processor = context.createScriptProcessor(2048, 2, 2);
  const silent = context.createGain();
  silent.gain.value = 0;
  processor.connect(silent);
  silent.connect(context.destination);
  const sources = new WeakMap();
  let pending = 0;
  processor.onaudioprocess = event => {
    if (pending >= 3 || !window.__visionTrackAudio) return;
    const input = event.inputBuffer;
    const left = input.getChannelData(0);
    const right = input.numberOfChannels > 1 ? input.getChannelData(1) : left;
    const samples = new Array(left.length * 2);
    for (let i=0; i<left.length; i++) {
      samples[i*2] = left[i];
      samples[i*2+1] = right[i];
    }
    pending++;
    Promise.resolve(window.__visionTrackAudio(samples)).catch(()=>{}).finally(()=>pending--);
  };
  const attach = element => {
    if (sources.has(element)) return;
    const capture = element.captureStream || element.mozCaptureStream;
    if (!capture) return;
    try {
      const stream = capture.call(element);
      if (!stream.getAudioTracks().length) return;
      const node = context.createMediaStreamSource(stream);
      const gain = context.createGain();
      const updateVolume = () => gain.gain.value = element.muted ? 0 : element.volume;
      updateVolume();
      node.connect(gain);
      gain.connect(processor);
      element.addEventListener('volumechange', updateVolume);
      sources.set(element, node);
      context.resume().catch(()=>{});
      element.addEventListener('emptied', () => {
        try { node.disconnect(); gain.disconnect(); } catch (_) {}
        element.removeEventListener('volumechange', updateVolume);
        sources.delete(element);
      }, {once:true});
    } catch (_) { /* Cross-origin/protected media remains inaccessible. */ }
  };
  const inspect = () => document.querySelectorAll('audio,video').forEach(element => {
    attach(element);
    if (!element.__visionTrackAudioBound) {
      element.__visionTrackAudioBound = true;
      element.addEventListener('playing', () => attach(element));
      element.addEventListener('loadedmetadata', () => attach(element));
    }
  });
  document.addEventListener('DOMContentLoaded', () => {
    inspect();
    new MutationObserver(inspect).observe(document.documentElement, {childList:true, subtree:true});
    context.resume().catch(()=>{});
  }, {once:true});
})();'''


def accept_pcm(buffer, samples):
    import numpy as np
    if not isinstance(samples, list) or len(samples) > 8192 or len(samples) % 2:
        return False
    try:
        data = np.asarray(samples, dtype='float32').reshape(-1, 2)
    except (TypeError, ValueError):
        return False
    if not np.all(np.isfinite(data)):
        return False
    buffer.push(np.clip(data, -1, 1))
    return True
