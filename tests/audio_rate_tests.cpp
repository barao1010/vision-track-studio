#include "audio_rate.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <numbers>
#include <stdexcept>
using namespace vision;
void check(bool condition) {if(!condition) throw std::runtime_error("Audio rate contract failed");}
template<class F> void rejects(F action) {bool failed=false;try {action();}catch(const std::exception&) {failed=true;}check(failed);}
std::vector<float> convert(const std::vector<float>& input,int in,int out,int channels,std::size_t chunk) {
    AudioRateConverter converter(in,out,channels);std::vector<float> result;
    auto collect=[&](const AudioBlock& block) {check(block.channels==channels);check(block.start_sample==static_cast<std::int64_t>(result.size()/channels));result.insert(result.end(),block.samples.begin(),block.samples.end());};
    for(std::size_t at=0;at<input.size();) {
        auto end=std::min(input.size(),at+chunk*channels);
        collect(converter.append({static_cast<std::int64_t>(at/channels),channels,{input.begin()+at,input.begin()+end}}));at=end;
    }
    collect(converter.finish());check(converter.finish().samples.empty());
    rejects([&]{converter.append({0,channels,{}});});return result;
}
std::vector<float> tone(int rate,double hz,int channels) {
    std::vector<float> result;
    for(int i=0;i<rate;++i) for(int c=0;c<channels;++c)
        result.push_back(static_cast<float>(.5*std::sin(2*std::numbers::pi*hz*i/rate))*(c==0?1.f:-1.f));
    return result;
}
double rms(const std::vector<float>& data,int channels) {
    double sum=0;int count=0;
    for(std::size_t i=1000*channels;i<data.size()-1000*channels;i+=channels) {sum+=data[i]*data[i];++count;}
    return std::sqrt(sum/count);
}
int main() {
    const auto input=tone(44100,440,2);
    const auto full=convert(input,44100,48000,2,44100);
    const auto pieces=convert(input,44100,48000,2,137);
    check(full==pieces && full.size()==96000);
    check(std::abs(rms(full,2)-.5/std::sqrt(2))<.001);
    for(std::size_t i=0;i<full.size();i+=2) check(full[i]==-full[i+1]);
    // Compare against an independently sampled analytic tone, excluding edges.
    double error=0;
    for(int i=1000;i<47000;++i) error=std::max(error,std::abs(full[2*i]-.5*std::sin(2*std::numbers::pi*440*i/48000)));
    check(error<.0002);
    auto low=convert(tone(48000,1000,1),48000,16000,1,91);
    auto high=convert(tone(48000,12000,1),48000,16000,1,91);
    check(low.size()==16000 && high.size()==16000);
    check(std::abs(rms(low,1)-.5/std::sqrt(2))<.001);
    check(rms(high,1)<.001); // Reject aliasing into the speech band.
    check(convert(input,44100,44100,2,1)==input);
    check(convert({.25f},44100,48000,1,1)==std::vector<float>({.25f,.25f}));
    check(convert({},48000,44100,1,1).empty());
    AudioRateConverter valid(44100,48000,2);
    rejects([&]{valid.append({1,2,{.1f,.1f}});});
    rejects([&]{valid.append({0,1,{.1f}});});
    rejects([&]{valid.append({0,2,{.1f}});});
    rejects([&]{valid.append({0,2,{std::numeric_limits<float>::infinity(),0}});});
    valid.append({0,2,{.25f,.25f}});check(valid.finish().samples.size()==4);
    rejects([]{AudioRateConverter invalid(0,48000,2);});
    std::cout<<"PASS: rational timestamps, chunk invariance, stereo, tone accuracy, alias rejection, flush, malformed input\n";
}
