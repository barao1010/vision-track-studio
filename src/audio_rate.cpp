#include "audio_rate.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <numbers>
#include <stdexcept>
namespace vision {
namespace { constexpr int radius=32; }
AudioRateConverter::AudioRateConverter(int input_rate,int output_rate,int channels)
    :input_rate_(input_rate),output_rate_(output_rate),channels_(channels) {
    if(input_rate<8000 || input_rate>192000 || output_rate<8000 || output_rate>192000 || (channels!=1 && channels!=2))
        throw std::invalid_argument("Unsupported audio rate or channel count");
}
AudioBlock AudioRateConverter::append(const AudioBlock& input) {
    if(finished_) throw std::logic_error("Audio converter already finished");
    if(input.channels!=channels_ || input.start_sample!=received_ || input.samples.size()%channels_)
        throw std::invalid_argument("Audio converter requires contiguous complete frames");
    for(float value:input.samples) if(!std::isfinite(value)) throw std::invalid_argument("Non-finite audio sample");
    auto frames=input.samples.size()/channels_;
    // Bound all rational-clock multiplication before modifying stream state.
    constexpr auto limit=std::numeric_limits<std::int64_t>::max()/192000-1;
    if(frames>static_cast<std::size_t>(limit-received_)) throw std::overflow_error("Audio timeline too long");
    samples_.insert(samples_.end(),input.samples.begin(),input.samples.end());
    received_+=static_cast<std::int64_t>(frames);
    return produce(false);
}
AudioBlock AudioRateConverter::finish() {
    auto result=produce(true);finished_=true;return result;
}
AudioBlock AudioRateConverter::produce(bool final) {
    AudioBlock output{emitted_,channels_,{}};
    const auto count=(received_*output_rate_+input_rate_-1)/input_rate_;
    const double cutoff=.94*std::min(1.0,static_cast<double>(output_rate_)/input_rate_);
    while(emitted_<count) {
        const auto numerator=emitted_*input_rate_;
        const auto center=numerator/output_rate_;
        if(!final && center+radius>=received_) break;
        const double fraction=static_cast<double>(numerator%output_rate_)/output_rate_;
        double sum[2]={},weight_sum=0;
        if(input_rate_==output_rate_) {
            for(int channel=0;channel<channels_;++channel)
                output.samples.push_back(samples_.at(static_cast<std::size_t>(center-base_)*channels_+channel));
        } else {
            for(int offset=-radius+1;offset<=radius;++offset) {
                const double distance=offset-fraction;
                const double angle=std::numbers::pi*distance*cutoff;
                const double sinc=std::abs(angle)<1e-12?1.0:std::sin(angle)/angle;
                const double window=.5+.5*std::cos(std::numbers::pi*distance/radius);
                const double weight=cutoff*sinc*window;
                const auto index=std::clamp(center+offset,std::int64_t{0},received_-1);
                for(int channel=0;channel<channels_;++channel)
                    sum[channel]+=weight*samples_.at(static_cast<std::size_t>(index-base_)*channels_+channel);
                weight_sum+=weight;
            }
            for(int channel=0;channel<channels_;++channel) output.samples.push_back(static_cast<float>(sum[channel]/weight_sum));
        }
        ++emitted_;
    }
    const auto keep=std::max(std::int64_t{0},emitted_*input_rate_/output_rate_-radius);
    while(base_<keep && base_<received_) {
        for(int channel=0;channel<channels_;++channel) samples_.pop_front();
        ++base_;
    }
    return output;
}
}
