#define NOMINMAX
#include "windows_recording.hpp"
#include <windows.h>
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <wrl/client.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <sstream>
#include <stdexcept>
using Microsoft::WRL::ComPtr;
namespace vision {
namespace {
void checked(HRESULT result,const char* operation) {
    if(FAILED(result)) {std::ostringstream text;text<<operation<<" failed: HRESULT 0x"<<std::hex<<static_cast<unsigned long>(result);throw std::runtime_error(text.str());}
}
ComPtr<IMFMediaType> media() {ComPtr<IMFMediaType> type;checked(MFCreateMediaType(&type),"Create media type");return type;}
void videoType(IMFMediaType* t,const GUID& subtype,int w,int h,int fps) {
    checked(t->SetGUID(MF_MT_MAJOR_TYPE,MFMediaType_Video),"Video type");
    checked(t->SetGUID(MF_MT_SUBTYPE,subtype),"Video subtype");
    checked(t->SetUINT32(MF_MT_INTERLACE_MODE,MFVideoInterlace_Progressive),"Interlace");
    checked(MFSetAttributeSize(t,MF_MT_FRAME_SIZE,w,h),"Frame size");
    checked(MFSetAttributeRatio(t,MF_MT_FRAME_RATE,fps,1),"Frame rate");
    checked(MFSetAttributeRatio(t,MF_MT_PIXEL_ASPECT_RATIO,1,1),"Pixel aspect");
}
void audioType(IMFMediaType* t,const GUID& subtype,int rate) {
    checked(t->SetGUID(MF_MT_MAJOR_TYPE,MFMediaType_Audio),"Audio type");
    checked(t->SetGUID(MF_MT_SUBTYPE,subtype),"Audio subtype");
    checked(t->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS,2),"Audio channels");
    checked(t->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND,rate),"Audio sample rate");
    checked(t->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE,16),"Audio bit depth");
}
BYTE srgb(float l) {l=std::clamp(l,0.f,1.f);return static_cast<BYTE>(std::lround(255*(l<=.0031308f?12.92f*l:1.055f*std::pow(l,1.f/2.4f)-.055f)));}
void sample(IMFSinkWriter* writer,DWORD stream,const void* data,DWORD size,LONGLONG time,LONGLONG duration) {
    ComPtr<IMFMediaBuffer> buffer;checked(MFCreateMemoryBuffer(size,&buffer),"Create sample buffer");
    BYTE* dest=nullptr;checked(buffer->Lock(&dest,nullptr,nullptr),"Lock sample buffer");
    std::memcpy(dest,data,size);checked(buffer->Unlock(),"Unlock sample buffer");checked(buffer->SetCurrentLength(size),"Set buffer length");
    ComPtr<IMFSample> packet;checked(MFCreateSample(&packet),"Create sample");checked(packet->AddBuffer(buffer.Get()),"Attach buffer");
    checked(packet->SetSampleTime(time),"Sample time");checked(packet->SetSampleDuration(duration),"Sample duration");checked(writer->WriteSample(stream,packet.Get()),"Encode sample");
}
}
struct WindowsRecorder::State {
    ComPtr<IMFSinkWriter> writer;
    DWORD video=0,audio=0;
    int width=0,height=0,fps=0,rate=0;
    std::int64_t frames=0,samples=0;
    bool finished=false,failed=false;
};
WindowsRecorder::WindowsRecorder(const std::filesystem::path& path,int w,int h,int fps,int rate):state_(std::make_unique<State>()) {
    if(w<=0 || h<=0 || w>4096 || h>4096 || w%2 || h%2 || fps<1 || fps>120 || rate!=48000) throw std::invalid_argument("Unsupported recording format");
    if(std::filesystem::exists(path)) throw std::invalid_argument("Recording file already exists");
    auto& s=*state_;s.width=w;s.height=h;s.fps=fps;s.rate=rate;
    ComPtr<IMFAttributes> options;checked(MFCreateAttributes(&options,2),"Recorder attributes");
    checked(options->SetUINT32(MF_SINK_WRITER_DISABLE_THROTTLING,TRUE),"Disable throttling");
    checked(MFCreateSinkWriterFromURL(path.c_str(),nullptr,options.Get(),&s.writer),"Open MP4 writer");
    auto output=media();videoType(output.Get(),MFVideoFormat_H264,w,h,fps);
    checked(output->SetUINT32(MF_MT_AVG_BITRATE,4000000),"Video bitrate");
    checked(s.writer->AddStream(output.Get(),&s.video),"Add video stream");
    auto input=media();videoType(input.Get(),MFVideoFormat_RGB32,w,h,fps);
    checked(input->SetUINT32(MF_MT_DEFAULT_STRIDE,w*4),"Video stride");
    checked(s.writer->SetInputMediaType(s.video,input.Get(),nullptr),"Set video input");
    auto encoded=media();audioType(encoded.Get(),MFAudioFormat_AAC,rate);
    checked(encoded->SetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND,24000),"Audio bitrate");
    checked(encoded->SetUINT32(MF_MT_AAC_PAYLOAD_TYPE,0),"AAC payload");
    checked(encoded->SetUINT32(MF_MT_AAC_AUDIO_PROFILE_LEVEL_INDICATION,0x29),"AAC profile");
    checked(s.writer->AddStream(encoded.Get(),&s.audio),"Add audio stream");
    auto pcm=media();audioType(pcm.Get(),MFAudioFormat_PCM,rate);
    checked(pcm->SetUINT32(MF_MT_AUDIO_BLOCK_ALIGNMENT,4),"PCM alignment");
    checked(pcm->SetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND,rate*4),"PCM bitrate");
    checked(s.writer->SetInputMediaType(s.audio,pcm.Get(),nullptr),"Set audio input");
    checked(s.writer->BeginWriting(),"Begin MP4");
}
WindowsRecorder::~WindowsRecorder()=default;
void WindowsRecorder::append(const Frame& frame,const AudioBlock& audio) {
    auto& s=*state_;
    if(s.finished || s.failed) throw std::logic_error("Recorder is closed or failed");
    auto next=(s.frames+1)*s.rate/s.fps;
    if(frame.width()!=s.width || frame.height()!=s.height || audio.channels!=2 || audio.start_sample!=s.samples || audio.samples.size()!=static_cast<std::size_t>(next-s.samples)*2) throw std::invalid_argument("Audio/video timeline mismatch");
    std::vector<BYTE> pixels(static_cast<std::size_t>(s.width)*s.height*4);
    for(int y=0;y<s.height;++y) for(int x=0;x<s.width;++x) {
        auto p=frame.at(x,y);if(!std::isfinite(p.r)||!std::isfinite(p.g)||!std::isfinite(p.b)||!std::isfinite(p.a)) throw std::invalid_argument("Nonfinite pixel");
        // Sink writer consumes these positive-stride RGB32 buffers in top-down order.
        auto n=(static_cast<std::size_t>(y)*s.width+x)*4;float a=std::clamp(p.a,0.f,1.f);
        pixels[n]=srgb(p.b*a);pixels[n+1]=srgb(p.g*a);pixels[n+2]=srgb(p.r*a);
    }
    std::vector<std::int16_t> pcm;pcm.reserve(audio.samples.size());
    for(float v:audio.samples) {if(!std::isfinite(v)) throw std::invalid_argument("Nonfinite sample");pcm.push_back(static_cast<std::int16_t>(std::lround(std::clamp(v,-1.f,1.f)*32767)));}
    auto time=s.frames*10000000/s.fps, end=(s.frames+1)*10000000/s.fps;
    try {
        sample(s.writer.Get(),s.video,pixels.data(),static_cast<DWORD>(pixels.size()),time,end-time);
        sample(s.writer.Get(),s.audio,pcm.data(),static_cast<DWORD>(pcm.size()*2),s.samples*10000000/s.rate,(next*10000000/s.rate)-(s.samples*10000000/s.rate));
    }catch(...) {s.failed=true;throw;}
    ++s.frames;s.samples=next;
}
void WindowsRecorder::finish() {
    auto& s=*state_;if(s.finished) return;
    if(s.failed) throw std::logic_error("Cannot finalize failed recording");
    checked(s.writer->Finalize(),"Finalize MP4");s.finished=true;s.writer.Reset();
}
}
