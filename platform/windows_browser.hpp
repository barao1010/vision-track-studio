#pragma once
#include "core.hpp"
#include <windows.h>
namespace vision {
// STA thread and a pumping Win32 message loop required. No browser audio yet.
class BrowserSource final : public VideoSource {
public:
    BrowserSource(std::wstring url,std::wstring css,int width,int height,
                  std::wstring local_html=L"");
    ~BrowserSource();
    Frame frame(std::int64_t timestamp_ns) const override;
private:
    struct State;
    std::shared_ptr<State> state_;
};
}
