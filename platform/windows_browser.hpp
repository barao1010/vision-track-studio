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
    void set_css(std::wstring css) const;
    void reload() const;
    void navigate(std::wstring url) const;
    Frame frame(std::int64_t timestamp_ns) const override;
private:
    struct State;
    static void apply_css(const std::shared_ptr<State>& state);
    std::shared_ptr<State> state_;
};
}
