#define NOMINMAX
#include "windows_microphone.hpp"
#include "audio_rate.hpp"
#include "audio_buffer.hpp"
#include <windows.h>
#include <audioclient.h>
#include <mmdeviceapi.h>
#include <mmreg.h>
#include <functiondiscoverykeys_devpkey.h>
#include <limits>
#include <wrl/client.h>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <future>
#include <mutex>
#include <sstream>
#include <thread>
using Microsoft::WRL::ComPtr;
namespace vision {
namespace {
void checked(HRESULT result,const char* operation) {
    if(FAILED(result)) {std::ostringstream message;message<<operation<<" failed: HRESULT 0x"<<std::hex<<static_cast<unsigned long>(result);throw std::runtime_error(message.str());}
}
struct Event {
    HANDLE value=CreateEvent(nullptr,FALSE,FALSE,nullptr);
    Event() {if(!value) throw std::runtime_error("Could not create capture event");}
    ~Event() {CloseHandle(value);}
};
struct ComScope {
    ComScope() {checked(CoInitializeEx(nullptr,COINIT_MULTITHREADED),"Capture COM initialization");}
    ~ComScope() {CoUninitialize();}
};
std::int64_t packetTime(UINT64 qpc100ns) {
    LARGE_INTEGER ticks{},frequency{};QueryPerformanceFrequency(&frequency);QueryPerformanceCounter(&ticks);
    const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
    const long double current100ns=static_cast<long double>(ticks.QuadPart)*10000000/frequency.QuadPart;
    const auto age=static_cast<std::int64_t>((current100ns-qpc100ns)*100);
    if(age < -100000000 || age>10000000000LL) throw std::runtime_error("Invalid microphone packet timestamp");
    return ns-age;
}
}
std::vector<MicrophoneDevice> microphone_devices() {
    ComPtr<IMMDeviceEnumerator> enumerator;
    checked(CoCreateInstance(__uuidof(MMDeviceEnumerator),nullptr,CLSCTX_ALL,IID_PPV_ARGS(&enumerator)),"Enumerate microphones");
    ComPtr<IMMDeviceCollection> collection;
    checked(enumerator->EnumAudioEndpoints(eCapture,DEVICE_STATE_ACTIVE,&collection),"List capture endpoints");
    UINT count=0;checked(collection->GetCount(&count),"Count microphones");
    std::vector<MicrophoneDevice> devices;
    for(UINT i=0;i<count;++i) {
        ComPtr<IMMDevice> device;checked(collection->Item(i,&device),"Read capture endpoint");
        LPWSTR raw=nullptr;checked(device->GetId(&raw),"Read endpoint identity");
        std::unique_ptr<wchar_t,decltype(&CoTaskMemFree)> id(raw,CoTaskMemFree);
        ComPtr<IPropertyStore> properties;checked(device->OpenPropertyStore(STGM_READ,&properties),"Read microphone properties");
        struct Property {PROPVARIANT value{};~Property(){PropVariantClear(&value);}} name;
        checked(properties->GetValue(PKEY_Device_FriendlyName,&name.value),"Read microphone name");
        devices.push_back({id.get(),name.value.vt==VT_LPWSTR && name.value.pwszVal?name.value.pwszVal:id.get()});
    }
    return devices;
}
struct WindowsMicrophone::State {
    std::wstring endpoint_id;
    Event stop;
    std::thread worker;
    std::mutex mutex;
    std::condition_variable ready;
    AudioHistory history;
    std::string failure;
    void run(std::promise<void> started) {
        bool announced=false;
        try {
            ComScope com;
            ComPtr<IMMDeviceEnumerator> enumerator;
            checked(CoCreateInstance(__uuidof(MMDeviceEnumerator),nullptr,CLSCTX_ALL,IID_PPV_ARGS(&enumerator)),"Enumerate microphones");
            ComPtr<IMMDevice> device;
            if(endpoint_id.empty()) checked(enumerator->GetDefaultAudioEndpoint(eCapture,eConsole,&device),"Open default microphone");
            else checked(enumerator->GetDevice(endpoint_id.c_str(),&device),"Open selected microphone (no fallback)");
            ComPtr<IMMEndpoint> endpoint;checked(device.As(&endpoint),"Read endpoint type");
            EDataFlow flow=eAll;checked(endpoint->GetDataFlow(&flow),"Check capture endpoint");
            DWORD status=0;checked(device->GetState(&status),"Check microphone state");
            if(flow!=eCapture || status!=DEVICE_STATE_ACTIVE) throw std::runtime_error("Selected microphone is not an active capture endpoint");
            ComPtr<IAudioClient> client;checked(device->Activate(__uuidof(IAudioClient),CLSCTX_ALL,nullptr,reinterpret_cast<void**>(client.GetAddressOf())),"Activate microphone");
            WAVEFORMATEX* native=nullptr;checked(client->GetMixFormat(&native),"Read microphone format");
            const auto rate=native->nSamplesPerSec;const auto channels=native->nChannels;CoTaskMemFree(native);
            if(channels!=1 && channels!=2) throw std::runtime_error("Only mono/stereo microphones are supported");
            AudioRateConverter converter(static_cast<int>(rate),48000,channels);
            WAVEFORMATEX format{};format.wFormatTag=WAVE_FORMAT_IEEE_FLOAT;format.nChannels=channels;
            format.nSamplesPerSec=rate;format.wBitsPerSample=32;format.nBlockAlign=channels*4;format.nAvgBytesPerSec=rate*format.nBlockAlign;
            checked(client->Initialize(AUDCLNT_SHAREMODE_SHARED,AUDCLNT_STREAMFLAGS_EVENTCALLBACK|AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM,1000000,0,&format,nullptr),"Initialize microphone");
            Event packets;checked(client->SetEventHandle(packets.value),"Set microphone event");
            ComPtr<IAudioCaptureClient> capture;checked(client->GetService(IID_PPV_ARGS(&capture)),"Create microphone capture");
            checked(client->Start(),"Start microphone");
            struct StopClient {IAudioClient* client;~StopClient(){client->Stop();}} stopClient{client.Get()};
            started.set_value();announced=true;
            std::int64_t inputFrames=0,origin=0;
            UINT64 expectedDevice=0;bool first=true;
            HANDLE events[]={stop.value,packets.value};
            for(;;) {
                auto event=WaitForMultipleObjects(2,events,FALSE,2000);
                if(event==WAIT_OBJECT_0) break;
                if(event==WAIT_TIMEOUT) throw std::runtime_error("Microphone stopped delivering audio");
                if(event!=WAIT_OBJECT_0+1) throw std::runtime_error("Microphone event wait failed");
                UINT32 available=0;checked(capture->GetNextPacketSize(&available),"Read microphone packet size");
                while(available) {
                    BYTE* bytes=nullptr;UINT32 frames=0;DWORD flags=0;UINT64 devicePosition=0,qpc=0;
                    checked(capture->GetBuffer(&bytes,&frames,&flags,&devicePosition,&qpc),"Read microphone samples");
                    AudioBlock input{inputFrames,channels,{}};
                    try {
                        if(flags&AUDCLNT_BUFFERFLAGS_TIMESTAMP_ERROR) throw std::runtime_error("Microphone timestamp unavailable");
                        if(!first && ((flags&AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY) || devicePosition!=expectedDevice)) throw std::runtime_error("Microphone audio discontinuity; restart capture");
                        if(first) origin=audio_sample_time(packetTime(qpc));
                        input.samples.resize(static_cast<std::size_t>(frames)*channels,0);
                        if(!(flags&AUDCLNT_BUFFERFLAGS_SILENT)) std::memcpy(input.samples.data(),bytes,input.samples.size()*sizeof(float));
                    } catch(...) {capture->ReleaseBuffer(frames);throw;}
                    checked(capture->ReleaseBuffer(frames),"Release microphone packet");
                    first=false;expectedDevice=devicePosition+frames;inputFrames+=frames;
                    auto converted=converter.append(input);
                    if(!converted.samples.empty()) {
                        AudioBlock stereo{origin+converted.start_sample,2,{}};
                        if(channels==2) stereo.samples=std::move(converted.samples);
                        else {stereo.samples.reserve(converted.samples.size()*2);for(float sample:converted.samples) {stereo.samples.push_back(sample);stereo.samples.push_back(sample);}}
                        {std::lock_guard lock(mutex);history.append(stereo);}ready.notify_all();
                    }
                    checked(capture->GetNextPacketSize(&available),"Read next microphone packet size");
                }
            }
        }catch(const std::exception& e) {
            {std::lock_guard lock(mutex);failure=e.what();}ready.notify_all();
            if(!announced) started.set_exception(std::current_exception());
        }
    }
};
WindowsMicrophone::WindowsMicrophone(std::wstring endpoint_id):state_(std::make_unique<State>()) {
    if(endpoint_id.size()>32768 || endpoint_id.find(L'\0')!=std::wstring::npos) throw std::invalid_argument("Invalid microphone endpoint identity");
    state_->endpoint_id=std::move(endpoint_id);
    std::promise<void> started;auto future=started.get_future();
    state_->worker=std::thread([s=state_.get(),promise=std::move(started)]() mutable {s->run(std::move(promise));});
    try {future.get();}catch(...) {state_->worker.join();throw;}
}
WindowsMicrophone::~WindowsMicrophone() {SetEvent(state_->stop.value);state_->worker.join();}
AudioBlock WindowsMicrophone::read(std::int64_t start,std::size_t frames) {
    if(start<0 || frames>48000 || start>std::numeric_limits<std::int64_t>::max()-static_cast<std::int64_t>(frames)) throw std::invalid_argument("Invalid microphone read");
    auto& s=*state_;std::unique_lock lock(s.mutex);
    if(!s.ready.wait_for(lock,std::chrono::milliseconds(500),[&]{return !s.failure.empty() || s.history.end()>=start+static_cast<std::int64_t>(frames);})) throw std::runtime_error("Timed out waiting for microphone audio");
    if(!s.failure.empty()) throw std::runtime_error(s.failure);
    return s.history.read(start,frames);
}
}
