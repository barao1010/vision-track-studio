#pragma once
#include "core.hpp"
namespace vision {
// Captures the Windows virtual desktop. Protected content may be unavailable.
class DesktopSource final : public VideoSource {
public:
    DesktopSource(int width=640,int height=360):width_(width),height_(height) {}
    Frame frame(std::int64_t timestamp_ns) const override;
private:
    int width_,height_;
};
}
