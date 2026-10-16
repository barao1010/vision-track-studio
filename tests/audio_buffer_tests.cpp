#include "audio_buffer.hpp"
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace vision;
void check(bool ok) {if(!ok) throw std::runtime_error("Audio history contract failed");}
template<class F> void rejects(F f) {bool failed=false;try {f();}catch(const std::exception&) {failed=true;}check(failed);}
int main() {
    AudioHistory late(5);
    late.append({48000,2,{.5f,-.5f}});
    check(late.read(47998,3).samples==std::vector<float>({0,0,0,0,.5f,-.5f}));
    AudioHistory history(5);
    history.append({0,2,{1,-1,2,-2}});
    history.append({3,2,{3,-3}});
    check(history.read(0,5).samples==std::vector<float>({1,-1,2,-2,0,0,3,-3,0,0}));
    rejects([&]{history.append({3,2,{4,4}});});
    history.append({4,2,{4,-4,5,-5}});
    rejects([&]{history.read(0,1);});
    check(history.read(1,5).samples==std::vector<float>({2,-2,0,0,3,-3,4,-4,5,-5}));
    history.append({1000000,2,{6,-6}});
    check(history.end()==1000001 && history.read(1000000,1).samples==std::vector<float>({6,-6}));
    history.append({1000001,2,std::vector<float>(20,.25f)});
    rejects([&]{history.read(1000001,1);});
    check(history.read(1000006,5).samples==std::vector<float>(10,.25f));
    rejects([&]{history.append({history.end(),2,{std::numeric_limits<float>::quiet_NaN(),0}});});
    check(audio_sample_time(1000000000)==48000);
    check(audio_sample_time(33333334)==1600);
    check(audio_sample_time(std::numeric_limits<std::int64_t>::max())>0);
    std::cout<<"PASS: capture packet gaps, stereo, bounded history, expired/overlapping packets, overflow-safe clock\n";
}
