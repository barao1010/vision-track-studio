#pragma once
#include "core.hpp"
#include <memory>
#include <string>
#include <vector>
namespace vision {
struct MicrophoneDevice {std::wstring id,name;};
// Requires COM initialized; enumeration does not activate capture.
std::vector<MicrophoneDevice> microphone_devices();
// Captures a selected Windows microphone on an owned COM worker. Device loss
// is surfaced as an error; it never silently changes the selected device.
class WindowsMicrophone {
public:
    explicit WindowsMicrophone(std::wstring endpoint_id=L"");
    ~WindowsMicrophone();
    WindowsMicrophone(const WindowsMicrophone&)=delete;
    WindowsMicrophone& operator=(const WindowsMicrophone&)=delete;
    AudioBlock read(std::int64_t absolute_start_sample,std::size_t frames);
private:
    struct State;
    std::unique_ptr<State> state_;
};
}
