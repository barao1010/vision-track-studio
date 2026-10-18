#pragma once
#include <stdexcept>
namespace vision {
inline int recording_audio_frames(int fps) {
    if(fps!=24 && fps!=25 && fps!=30 && fps!=50 && fps!=60)
        throw std::invalid_argument("Supported recording rates: 24, 25, 30, 50 and 60 fps");
    return 48000/fps;
}
}
