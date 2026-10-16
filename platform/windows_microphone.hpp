#pragma once
#include "core.hpp"
#include <memory>
namespace vision {
// Captures the default Windows microphone on an owned COM worker. Device loss
// is surfaced as an error; it never silently changes the selected device.
class WindowsMicrophone {
public:
    WindowsMicrophone();
    ~WindowsMicrophone();
    WindowsMicrophone(const WindowsMicrophone&)=delete;
    WindowsMicrophone& operator=(const WindowsMicrophone&)=delete;
    AudioBlock read(std::int64_t absolute_start_sample,std::size_t frames);
private:
    struct State;
    std::unique_ptr<State> state_;
};
}
