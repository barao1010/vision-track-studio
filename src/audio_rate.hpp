#pragma once
#include "core.hpp"
#include <deque>
namespace vision {
// Streaming, windowed-sinc rate conversion. Input timestamps are contiguous,
// zero-based source frames; output timestamps are destination frames. Retains
// 32 source frames of lookahead. finish() pads the last edge, never adds duration.
class AudioRateConverter {
public:
    AudioRateConverter(int input_rate, int output_rate, int channels);
    AudioBlock append(const AudioBlock& input);
    AudioBlock finish();
private:
    AudioBlock produce(bool final);
    int input_rate_, output_rate_, channels_;
    std::int64_t received_=0, emitted_=0, base_=0;
    bool finished_=false;
    std::deque<float> samples_;
};
}
