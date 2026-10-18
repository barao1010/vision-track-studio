#include "scheduled_output.hpp"
#include <iostream>
#include <stdexcept>
using namespace vision;
void check(bool value) {if(!value) throw std::runtime_error("Scheduled output contract failed");}
struct State {
    std::mutex mutex;
    std::condition_variable changed;
    std::vector<OutputPacket> packets;
    bool blocked=false,release=false,finished=false,destroyed=false;
    std::thread::id owner;
};
class Sink final:public OutputSink {
    State& state_;
public:
    explicit Sink(State& state):state_(state) {state_.owner=std::this_thread::get_id();}
    ~Sink() {std::lock_guard lock(state_.mutex);state_.destroyed=std::this_thread::get_id()==state_.owner;}
    Meter write(const OutputPacket& packet) override {
        check(std::this_thread::get_id()==state_.owner);
        std::unique_lock lock(state_.mutex);state_.packets.push_back(packet);
        if(state_.packets.size()==2) {
            state_.blocked=true;state_.changed.notify_all();
            state_.changed.wait(lock,[&]{return state_.release;});
        }
        state_.changed.notify_all();return {.5f,.25f};
    }
    void finish() override {check(std::this_thread::get_id()==state_.owner);std::lock_guard lock(state_.mutex);state_.finished=true;}
};
int main() {
    State state;auto red=std::make_shared<Frame>(1,1,Pixel{1,0,0,1}),blue=std::make_shared<Frame>(1,1,Pixel{0,0,1,1});
    ScheduledOutput output([&]{return std::make_unique<Sink>(state);},red);
    {
        std::unique_lock lock(state.mutex);
        check(state.changed.wait_for(lock,std::chrono::seconds(3),[&]{return state.blocked;}));
    }
    // A blocked encoder must not hold the snapshot lock or build a producer queue.
    for(int n=0;n<1000;++n) output.update(n%2?blue:red,2,true);
    {std::lock_guard lock(state.mutex);state.release=true;}state.changed.notify_all();
    {
        std::unique_lock lock(state.mutex);
        check(state.changed.wait_for(lock,std::chrono::seconds(3),[&]{return state.packets.size()>=4;}));
    }
    output.finish();output.finish();
    check(state.finished && state.destroyed && state.owner!=std::this_thread::get_id());
    for(std::size_t n=0;n<state.packets.size();++n) {
        check(state.packets[n].frame_number==static_cast<std::int64_t>(n));
        check(state.packets[n].audio_start==state.packets[0].audio_start+static_cast<std::int64_t>(n)*1600);
    }
    check(state.packets[0].frame->at(0,0).r==1 && state.packets[1].frame->at(0,0).r==1);
    check(state.packets[2].frame->at(0,0).b==1 && state.packets[2].gain==2 && state.packets[2].muted);
    bool failed=false;try {output.update(red,1,false);}catch(const std::logic_error&) {failed=true;}check(failed);
    failed=false;try {ScheduledOutput broken([]()->std::unique_ptr<OutputSink>{throw std::runtime_error("init");},red);}catch(const std::runtime_error&) {failed=true;}check(failed);
    std::cout<<"PASS: independent output clock, held frames, contiguous audio, bounded latest snapshot, gain/mute, thread affinity and shutdown\n";
}
