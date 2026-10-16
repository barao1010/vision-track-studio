#pragma once
#include "core.hpp"
#include <filesystem>
#include <fstream>
namespace vision {
// P6 portable pixmap: a dependency-free file source, not a general image decoder.
Frame read_ppm(const std::filesystem::path& path);
// Uncompressed interchange recorder. Encoded containers are a separate adapter.
class RawRecorder {
public:
    RawRecorder(const std::filesystem::path& directory,int width,int height,int fps,int rate);
    void append(const Frame& frame,const AudioBlock& audio);
    void finish();
private:
    std::ofstream video_,audio_,manifest_;
    int width_,height_,fps_,rate_;
    std::int64_t frames_=0, samples_=0;
    bool finished_=false;
};
}
