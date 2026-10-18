#pragma once
#include "core.hpp"
#include <memory>
#include <string>
#include <vector>
#include <mfobjects.h>
namespace vision {
struct CameraDevice { std::wstring id,name; };
// Caller owns COM/MF startup. IDs are persistent symbolic links, not list indexes.
std::vector<CameraDevice> camera_devices();
Frame camera_rgb32(IMFMediaBuffer* buffer,int width,int height,long default_stride);
class CameraSource final : public VideoSource {
public:
    explicit CameraSource(const std::wstring& device_id);
    ~CameraSource();
    void reconnect() const;
    Frame frame(std::int64_t timestamp_ns) const override;
private:
    struct Impl;
    std::wstring device_;
    mutable std::unique_ptr<Impl> impl_;
};
}
