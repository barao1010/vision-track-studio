#pragma once
#include "core.hpp"
#include <deque>
namespace vision {
// Bounded 48kHz stereo capture history. Caller owns synchronization.
class AudioHistory {
public:
    explicit AudioHistory(std::size_t capacity_frames=480000);
    void append(const AudioBlock& stereo);
    AudioBlock read(std::int64_t start, std::size_t frames) const;
    std::int64_t end() const { return end_; }
private:
    std::size_t capacity_;
    std::int64_t begin_=0,end_=0,expired_=0;
    std::deque<float> samples_;
};
std::int64_t audio_sample_time(std::int64_t timestamp_ns);
}
