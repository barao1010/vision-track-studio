#pragma once
#include <cstdint>
#include <memory>
#include <string>
#include <vector>
#include <span>

namespace vision {
// Linear-light, straight-alpha pixels. Output adapters own colour conversion.
struct Pixel { float r=0, g=0, b=0, a=0; };
class Frame {
public:
    Frame(int width, int height, Pixel fill={});
    int width() const { return width_; }
    int height() const { return height_; }
    std::span<Pixel> row(int y);
    std::span<const Pixel> row(int y) const;
    Pixel& at(int x, int y);
    const Pixel& at(int x, int y) const;
private:
    int width_, height_;
    std::vector<Pixel> pixels_;
};
class VideoSource {
public:
    virtual ~VideoSource() = default;
    virtual Frame frame(std::int64_t timestamp_ns) const = 0;
};
class StillSource final : public VideoSource {
public:
    explicit StillSource(Frame value) : value_(std::move(value)) {}
    Frame frame(std::int64_t) const override { return value_; }
private:
    Frame value_;
};
struct Crop { int left=0, top=0, right=0, bottom=0; };
struct Item {
    std::string id;
    std::shared_ptr<const VideoSource> source;
    int x=0, y=0, width=1, height=1;
    Crop crop;
    float opacity=1;
    bool visible=true;
};
class Scene {
public:
    void add(Item item);
    void remove(const std::string& id);
    void move(const std::string& id, std::size_t position);
    Item& item(const std::string& id);
    // Validates against the current source frame before changing the item.
    void transform(const std::string& id,int x,int y,int width,int height,
                   Crop crop,float opacity,std::int64_t timestamp_ns);
    Frame render(int width, int height, std::int64_t timestamp_ns) const;
private:
    std::vector<Item> items_; // bottom to top
};
class Switcher {
public:
    Switcher(int width, int height, std::shared_ptr<const Scene> initial);
    void take(std::shared_ptr<const Scene> next, std::int64_t now_ns,
              std::int64_t duration_ns);
    Frame render(std::int64_t now_ns);
private:
    int width_, height_;
    std::shared_ptr<const Scene> current_, target_;
    std::unique_ptr<Frame> interrupted_;
    std::int64_t start_=0, duration_=0, clock_=-1;
    void check_time(std::int64_t now);
};
struct AudioBlock {
    std::int64_t start_sample=0;
    int channels=2;
    std::vector<float> samples; // interleaved; already resampled to mixer rate
};
struct AudioInput {
    const AudioBlock* block=nullptr;
    float gain=1;
    bool muted=false;
};
struct Meter { float peak=0, rms=0; };
struct MixedAudio { AudioBlock block; Meter meter; };
MixedAudio mix(std::int64_t start, std::size_t frames, int channels,
               const std::vector<AudioInput>& inputs);
}
