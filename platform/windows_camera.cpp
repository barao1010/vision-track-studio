#define NOMINMAX
#include "windows_camera.hpp"
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <mferror.h>
#include <wrl.h>
#include <chrono>
#include <cmath>
#include <mutex>
#include <stdexcept>
#include <limits>
namespace vision {
using Microsoft::WRL::ComPtr;
namespace {
void check(HRESULT hr) {
    if(FAILED(hr)) throw std::runtime_error("Camera operation failed (HRESULT "+std::to_string(static_cast<unsigned long>(hr))+")");
}
std::wstring attribute(IMFAttributes* object,REFGUID key) {
    wchar_t* raw=nullptr;UINT32 length=0;check(object->GetAllocatedString(key,&raw,&length));
    std::unique_ptr<wchar_t,decltype(&CoTaskMemFree)> value(raw,CoTaskMemFree);
    return {raw,length};
}
float linear(BYTE b) {float s=b/255.f;return s<=.04045f?s/12.92f:std::pow((s+.055f)/1.055f,2.4f);}
struct Lock {
    ComPtr<IMFMediaBuffer> buffer;
    ComPtr<IMF2DBuffer> image;
    bool locked=false,two=false;
    ~Lock() {if(locked) {if(two) image->Unlock2D();else buffer->Unlock();}}
};
struct CaptureState {
    std::mutex mutex;
    std::shared_ptr<const Frame> latest;
    std::exception_ptr error;
    bool pending=false,stopped=false;
    int width=0,height=0;
    long stride=0;
    std::chrono::steady_clock::time_point last=std::chrono::steady_clock::now(),poll=last;
};
class Callback final : public Microsoft::WRL::RuntimeClass<Microsoft::WRL::RuntimeClassFlags<Microsoft::WRL::ClassicCom>,IMFSourceReaderCallback> {
public:
    explicit Callback(std::shared_ptr<CaptureState> state):state_(std::move(state)) {}
    STDMETHODIMP OnReadSample(HRESULT status,DWORD,DWORD flags,LONGLONG,IMFSample* sample) override {
        try {
            check(status);
            if(flags&(MF_SOURCE_READERF_ERROR|MF_SOURCE_READERF_ENDOFSTREAM|MF_SOURCE_READERF_CURRENTMEDIATYPECHANGED))
                throw std::runtime_error("Camera stopped or changed format; reconnect the selected device");
            std::shared_ptr<const Frame> frame;
            if(sample) {
                ComPtr<IMFMediaBuffer> buffer;check(sample->ConvertToContiguousBuffer(&buffer));
                frame=std::make_shared<Frame>(camera_rgb32(buffer.Get(),state_->width,state_->height,state_->stride));
            }
            std::lock_guard lock(state_->mutex);
            if(!state_->stopped && frame) {state_->latest=std::move(frame);state_->last=std::chrono::steady_clock::now();}
            state_->pending=false;
        } catch(...) {
            std::lock_guard lock(state_->mutex);state_->error=std::current_exception();state_->pending=false;
        }
        return S_OK;
    }
    STDMETHODIMP OnFlush(DWORD) override {return S_OK;}
    STDMETHODIMP OnEvent(DWORD,IMFMediaEvent*) override {return S_OK;}
private:
    std::shared_ptr<CaptureState> state_;
};
}
std::vector<CameraDevice> camera_devices() {
    ComPtr<IMFAttributes> attributes;check(MFCreateAttributes(&attributes,1));
    check(attributes->SetGUID(MF_DEVSOURCE_ATTRIBUTE_SOURCE_TYPE,MF_DEVSOURCE_ATTRIBUTE_SOURCE_TYPE_VIDCAP_GUID));
    IMFActivate** raw=nullptr;UINT32 count=0;check(MFEnumDeviceSources(attributes.Get(),&raw,&count));
    struct List { IMFActivate** data;UINT32 count;~List(){for(UINT32 i=0;i<count;++i)data[i]->Release();CoTaskMemFree(data);} } list{raw,count};
    std::vector<CameraDevice> result;
    for(UINT32 i=0;i<count;++i) result.push_back({attribute(raw[i],MF_DEVSOURCE_ATTRIBUTE_SOURCE_TYPE_VIDCAP_SYMBOLIC_LINK),attribute(raw[i],MF_DEVSOURCE_ATTRIBUTE_FRIENDLY_NAME)});
    return result;
}
Frame camera_rgb32(IMFMediaBuffer* buffer,int width,int height,long default_stride) {
    if(!buffer || width<1 || height<1 || width>1920 || height>1080) throw std::invalid_argument("Invalid camera frame size");
    Lock lock;lock.buffer=buffer;BYTE* top=nullptr;LONG stride=default_stride;
    if(SUCCEEDED(buffer->QueryInterface(IID_PPV_ARGS(&lock.image)))) {
        check(lock.image->Lock2D(&top,&stride));lock.locked=true;lock.two=true;
    } else {
        DWORD length=0;check(buffer->Lock(&top,nullptr,&length));lock.locked=true;
        const auto pitch=std::abs(static_cast<long long>(stride));
        if(pitch<width*4LL || pitch*height>length) throw std::runtime_error("Truncated camera buffer");
        if(stride<0) top+=pitch*(height-1);
    }
    if(std::abs(static_cast<long long>(stride))<width*4LL) throw std::runtime_error("Invalid camera stride");
    Frame frame(width,height);
    for(int y=0;y<height;++y) {
        const BYTE* row=top+static_cast<std::ptrdiff_t>(y)*stride;
        for(int x=0;x<width;++x) frame.at(x,y)={linear(row[4*x+2]),linear(row[4*x+1]),linear(row[4*x]),1};
    }
    return frame;
}
struct CameraSource::Impl {
    std::shared_ptr<CaptureState> state=std::make_shared<CaptureState>();
    ComPtr<IMFMediaSource> source;
    ComPtr<IMFSourceReader> reader;
    ~Impl() {
        {std::lock_guard lock(state->mutex);state->stopped=true;}
        if(source) source->Shutdown();
        reader.Reset();source.Reset();
    }
};
CameraSource::CameraSource(const std::wstring& device):device_(device),impl_(std::make_unique<Impl>()) {
    if(device.empty()) throw std::invalid_argument("Select a camera device");
    ComPtr<IMFAttributes> attributes;check(MFCreateAttributes(&attributes,2));
    check(attributes->SetGUID(MF_DEVSOURCE_ATTRIBUTE_SOURCE_TYPE,MF_DEVSOURCE_ATTRIBUTE_SOURCE_TYPE_VIDCAP_GUID));
    check(attributes->SetString(MF_DEVSOURCE_ATTRIBUTE_SOURCE_TYPE_VIDCAP_SYMBOLIC_LINK,device.c_str()));
    check(MFCreateDeviceSource(attributes.Get(),&impl_->source));
    auto callback=Microsoft::WRL::Make<Callback>(impl_->state);
    ComPtr<IMFAttributes> options;check(MFCreateAttributes(&options,2));
    check(options->SetUnknown(MF_SOURCE_READER_ASYNC_CALLBACK,callback.Get()));
    check(options->SetUINT32(MF_SOURCE_READER_ENABLE_VIDEO_PROCESSING,TRUE));
    check(MFCreateSourceReaderFromMediaSource(impl_->source.Get(),options.Get(),&impl_->reader));
    check(impl_->reader->SetStreamSelection(MF_SOURCE_READER_ALL_STREAMS,FALSE));
    check(impl_->reader->SetStreamSelection(MF_SOURCE_READER_FIRST_VIDEO_STREAM,TRUE));
    ComPtr<IMFMediaType> best;double bestScore=std::numeric_limits<double>::max();
    for(DWORD n=0;;++n) {
        ComPtr<IMFMediaType> type;
        auto hr=impl_->reader->GetNativeMediaType(MF_SOURCE_READER_FIRST_VIDEO_STREAM,n,&type);
        if(hr==MF_E_NO_MORE_TYPES) break;
        check(hr);UINT32 w=0,h=0,num=0,den=0;
        if(FAILED(MFGetAttributeSize(type.Get(),MF_MT_FRAME_SIZE,&w,&h)) || !w || !h || w>1920 || h>1080) continue;
        double fps=30;
        if(SUCCEEDED(MFGetAttributeRatio(type.Get(),MF_MT_FRAME_RATE,&num,&den)) && den) fps=static_cast<double>(num)/den;
        double score=std::abs(static_cast<double>(w)-640)+std::abs(static_cast<double>(h)-360)+10*std::abs(fps-30);
        if(score<bestScore) {best=type;bestScore=score;}
    }
    if(!best) throw std::runtime_error("Camera has no supported mode up to 1920x1080");
    check(impl_->reader->SetCurrentMediaType(MF_SOURCE_READER_FIRST_VIDEO_STREAM,nullptr,best.Get()));
    ComPtr<IMFMediaType> rgb;check(MFCreateMediaType(&rgb));
    check(rgb->SetGUID(MF_MT_MAJOR_TYPE,MFMediaType_Video));check(rgb->SetGUID(MF_MT_SUBTYPE,MFVideoFormat_RGB32));
    check(impl_->reader->SetCurrentMediaType(MF_SOURCE_READER_FIRST_VIDEO_STREAM,nullptr,rgb.Get()));
    check(impl_->reader->GetCurrentMediaType(MF_SOURCE_READER_FIRST_VIDEO_STREAM,&rgb));
    UINT32 w=0,h=0,stride=0;check(MFGetAttributeSize(rgb.Get(),MF_MT_FRAME_SIZE,&w,&h));
    if(!w || !h || w>1920 || h>1080) throw std::runtime_error("Camera output dimensions unsupported");
    impl_->state->width=static_cast<int>(w);impl_->state->height=static_cast<int>(h);
    if(SUCCEEDED(rgb->GetUINT32(MF_MT_DEFAULT_STRIDE,&stride))) impl_->state->stride=static_cast<LONG>(stride);
    else check(MFGetStrideForBitmapInfoHeader(MFVideoFormat_RGB32.Data1,w,&impl_->state->stride));
}
CameraSource::~CameraSource()=default;
void CameraSource::reconnect() const {
    impl_.reset(); // Release the old device before trying to acquire the same identity.
    CameraSource replacement(device_);impl_=std::move(replacement.impl_);
}
Frame CameraSource::frame(std::int64_t) const {
    if(!impl_) throw std::runtime_error("Camera disconnected; reconnect the selected device");
    auto state=impl_->state;std::shared_ptr<const Frame> latest;bool request=false;
    {
        std::lock_guard lock(state->mutex);
        if(state->error) std::rethrow_exception(state->error);
        auto current=std::chrono::steady_clock::now();
        if(!state->pending && current-state->poll>std::chrono::seconds(5)) state->last=current;
        state->poll=current;
        if(std::chrono::steady_clock::now()-state->last>std::chrono::seconds(5)) throw std::runtime_error("Camera timed out; reconnect the selected device");
        latest=state->latest;
        if(!state->pending) {state->pending=true;request=true;}
    }
    if(request) {
        try {check(impl_->reader->ReadSample(MF_SOURCE_READER_FIRST_VIDEO_STREAM,0,nullptr,nullptr,nullptr,nullptr));}
        catch(...) {std::lock_guard lock(state->mutex);state->error=std::current_exception();throw;}
    }
    // Transparent while waiting for the first frame, never a fabricated camera feed.
    return latest?*latest:Frame(state->width,state->height);
}
}
