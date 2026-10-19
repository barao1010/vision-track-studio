#define NOMINMAX
#include "windows_output.hpp"
#include "windows_recording.hpp"
#include "windows_microphone.hpp"
#include "recording_rate.hpp"
#include "video_scale.hpp"
#include <windows.h>
#include <mfapi.h>
#include <cmath>
#include <numbers>
#include <stdexcept>
namespace vision {
namespace {
struct PlatformScope {
    PlatformScope() {
        if(FAILED(CoInitializeEx(nullptr,COINIT_MULTITHREADED))) throw std::runtime_error("Output COM initialization failed");
        if(FAILED(MFStartup(MF_VERSION))) {CoUninitialize();throw std::runtime_error("Output Media Foundation initialization failed");}
    }
    ~PlatformScope() {MFShutdown();CoUninitialize();}
};
class WindowsOutput final:public OutputSink {
    PlatformScope platform_;
    std::unique_ptr<WindowsMicrophone> microphone_;
    int audioFrames_;
    WindowsRecorder recorder_;
    bool synthetic_;
    int output_height_;
    std::shared_ptr<const Frame> previous_;
    std::unique_ptr<Frame> scaled_;
public:
    WindowsOutput(const std::filesystem::path& path,bool microphone,bool synthetic,int fps,int video_kbps,std::wstring microphone_id,int output_height)
        :microphone_(microphone?std::make_unique<WindowsMicrophone>(std::move(microphone_id)):nullptr),audioFrames_(recording_audio_frames(fps)),recorder_(path,recording_output_width(output_height),output_height,fps,48000,video_kbps),synthetic_(synthetic),output_height_(output_height) {}
    Meter write(const OutputPacket& packet) override {
        AudioBlock audio{packet.frame_number*audioFrames_,2,std::vector<float>(2*audioFrames_,0)};
        if(microphone_) {
            audio=microphone_->read(packet.audio_start,audioFrames_);
            audio.start_sample=packet.frame_number*audioFrames_;
        } else if(synthetic_) {
            for(int i=0;i<audioFrames_;++i) {
                auto value=static_cast<float>(.2*std::sin(2*std::numbers::pi*440*(audio.start_sample+i)/48000));
                audio.samples[2*i]=value;audio.samples[2*i+1]=value;
            }
        }
        auto mixed=mix(audio.start_sample,audioFrames_,2,{{&audio,packet.gain,packet.muted}});
        if(packet.frame->height()==output_height_ && packet.frame->width()==recording_output_width(output_height_)) recorder_.append(*packet.frame,mixed.block);
        else {
            if(previous_!=packet.frame) {
                scaled_=std::make_unique<Frame>(scale_frame(*packet.frame,recording_output_width(output_height_),output_height_));previous_=packet.frame;
            }
            recorder_.append(*scaled_,mixed.block);
        }
        return mixed.meter;
    }
    void finish() override {microphone_.reset();recorder_.finish();}
};
}
std::unique_ptr<OutputSink> create_windows_output(const std::filesystem::path& path,bool microphone,bool synthetic_test_audio,int fps,int video_kbps,std::wstring microphone_id,int output_height) {
    return std::make_unique<WindowsOutput>(path,microphone,synthetic_test_audio,fps,video_kbps,std::move(microphone_id),output_height);
}
}
