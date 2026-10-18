"""Decode Windows-native MP4 output; verifies actual encoded media, not file size."""
import sys
import av
import numpy as np
path = sys.argv[1]
fps = int(sys.argv[2]) if len(sys.argv)>2 else 30
height = int(sys.argv[3]) if len(sys.argv)>3 else 360
width = height*16//9
assert height in (360,720,1080)
with av.open(path) as container:
    stream = container.streams.video[0]
    assert stream.codec_context.name == 'h264'
    frames = list(container.decode(video=0))
    assert len(frames) == fps*3, len(frames)
    times = [float(f.pts*f.time_base) for f in frames]
    assert all(b>a for a,b in zip(times,times[1:]))
    assert abs(times[-1]-times[0]-(fps*3-1)/fps) < .002
    for frame in frames:
        pixels = frame.to_ndarray(format='rgb24')
        assert pixels.shape == (height,width,3)
        top = pixels[height//12:height*5//12,width*3//64:width*15//16].mean(axis=(0,1))
        bottom = pixels[height*7//12:height*11//12,width*3//64:width*15//16].mean(axis=(0,1))
        assert top[0]>230 and top[2]<20, ('top must be red',top)
        assert bottom[2]>230 and bottom[0]<20, ('bottom must be blue',bottom)
with av.open(path) as container:
    stream = container.streams.audio[0]
    assert stream.codec_context.name == 'aac'
    resampler = av.AudioResampler(format='fltp',layout='stereo',rate=48000)
    blocks = [out.to_ndarray() for frame in container.decode(audio=0) for out in resampler.resample(frame)]
    blocks.extend(out.to_ndarray() for out in resampler.resample(None))
    samples = np.concatenate(blocks,axis=1)
    assert samples.shape[0]==2 and 2.95*48000 <= samples.shape[1] <= 3.1*48000
    stable = samples[:,48000:96000]
    rms = np.sqrt(np.mean(stable**2,axis=1))
    assert np.all(abs(rms-.2/np.sqrt(2))<.01),rms
    for channel in stable:
        hz=np.fft.rfftfreq(len(channel),1/48000)[np.argmax(abs(np.fft.rfft(channel*np.hanning(len(channel)))))]
        assert abs(hz-440)<=1,hz
print(f'PASS: native MP4 H.264/AAC, {fps*3} frames at {fps}fps, orientation/colors, timestamps and stereo 440Hz level')
