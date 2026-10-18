#pragma once
#include <stdexcept>
namespace vision {
inline int recording_output_width(int height) {
    if(height!=360 && height!=720 && height!=1080) throw std::invalid_argument("Output height must be 360, 720 or 1080");
    return height*16/9;
}
inline int recording_video_bps(int kbps) {
    if(kbps<500 || kbps>50000) throw std::invalid_argument("Video bitrate must be between 500 and 50000 kbps");
    return kbps*1000;
}
inline int recording_audio_frames(int fps) {
    if(fps!=24 && fps!=25 && fps!=30 && fps!=50 && fps!=60)
        throw std::invalid_argument("Supported recording rates: 24, 25, 30, 50 and 60 fps");
    return 48000/fps;
}
}
