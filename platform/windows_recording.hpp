#pragma once
#include "core.hpp"
#include <filesystem>
#include <memory>
namespace vision {
// Requires COM and Media Foundation initialized on the calling thread.
// Uses installed Windows encoders, not OBS or a bundled FFmpeg build.
class WindowsRecorder {
public:
    WindowsRecorder(const std::filesystem::path& path,int width,int height,int fps,int sample_rate=48000,int video_kbps=4000);
    ~WindowsRecorder();
    WindowsRecorder(const WindowsRecorder&)=delete;
    WindowsRecorder& operator=(const WindowsRecorder&)=delete;
    void append(const Frame& frame,const AudioBlock& audio);
    void finish();
private:
    struct State;
    std::unique_ptr<State> state_;
};
}
