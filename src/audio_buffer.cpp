#include "audio_buffer.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace vision {
std::int64_t audio_sample_time(std::int64_t ns) {
    if(ns<0) throw std::invalid_argument("Negative capture clock");
    return (ns/1000000000)*48000+(ns%1000000000)*48000/1000000000;
}
AudioHistory::AudioHistory(std::size_t capacity):capacity_(capacity) {
    if(capacity<1 || capacity>4800000) throw std::invalid_argument("Invalid audio history size");
}
void AudioHistory::append(const AudioBlock& block) {
    if(block.channels!=2 || block.samples.size()%2 || block.start_sample<end_)
        throw std::invalid_argument("Invalid or overlapping capture packet");
    auto frames=block.samples.size()/2;
    if(frames>static_cast<std::size_t>(std::numeric_limits<std::int64_t>::max()-block.start_sample)) throw std::overflow_error("Audio history timeline overflow");
    for(float v:block.samples) if(!std::isfinite(v)) throw std::invalid_argument("Nonfinite capture sample");
    if(!frames) return;
    const auto next=block.start_sample+static_cast<std::int64_t>(frames);
    if(block.start_sample-end_>=static_cast<std::int64_t>(capacity_)) {expired_=end_;samples_.clear();begin_=block.start_sample;end_=block.start_sample;}
    auto gap=static_cast<std::size_t>(block.start_sample-end_);
    samples_.insert(samples_.end(),gap*2,0);
    if(frames>=capacity_) {
        samples_.assign(block.samples.end()-static_cast<std::ptrdiff_t>(capacity_*2),block.samples.end());
        begin_=next-static_cast<std::int64_t>(capacity_);expired_=begin_;
    } else {
        samples_.insert(samples_.end(),block.samples.begin(),block.samples.end());
        while(samples_.size()>capacity_*2) {samples_.pop_front();samples_.pop_front();++begin_;expired_=begin_;}
    }
    end_=next;
}
AudioBlock AudioHistory::read(std::int64_t start,std::size_t frames) const {
    if(start<0 || frames>capacity_ || frames>static_cast<std::size_t>(std::numeric_limits<std::int64_t>::max()-start)) throw std::invalid_argument("Invalid capture read range");
    if(start<expired_) throw std::out_of_range("Capture history expired");
    AudioBlock result{start,2,std::vector<float>(frames*2,0)};
    for(std::size_t i=0;i<frames;++i) {
        const auto position=start+static_cast<std::int64_t>(i);
        if(position>=begin_ && position<end_) {
            auto offset=static_cast<std::size_t>(position-begin_)*2;
            result.samples[2*i]=samples_.at(offset);result.samples[2*i+1]=samples_.at(offset+1);
        }
    }
    return result;
}
}
