#include "output_worker.hpp"
#include <future>
#include <iostream>
#include <stdexcept>
using namespace vision;
void check(bool ok) {if(!ok) throw std::runtime_error("Output worker contract failed");}
template<class F> void rejects(F fn) {bool failed=false;try {fn();}catch(const std::exception&) {failed=true;}check(failed);}
struct State {
    std::promise<void> entered,release;
    std::shared_future<void> gate=release.get_future().share();
    std::thread::id owner;
    std::vector<std::int64_t> seen;
    bool finalized=false,destroyed=false,fail=false;
};
struct Sink:OutputSink {
    State& s;
    explicit Sink(State& state):s(state) {s.owner=std::this_thread::get_id();}
    ~Sink() override {s.destroyed=std::this_thread::get_id()==s.owner;}
    Meter write(const OutputPacket& p) override {
        check(std::this_thread::get_id()==s.owner);
        if(p.frame_number==0) {s.entered.set_value();s.gate.wait();}
        if(s.fail) throw std::runtime_error("Injected encoder failure");
        s.seen.push_back(p.frame_number);return {.5f,.25f};
    }
    void finish() override {check(std::this_thread::get_id()==s.owner);s.finalized=true;}
};
OutputPacket packet(int n) {return {std::make_shared<Frame>(1,1),n,n*1600,1,false};}
int main() {
    State state;
    OutputWorker worker([&]{return std::make_unique<Sink>(state);},2);
    check(state.owner!=std::this_thread::get_id());
    worker.enqueue(packet(0));state.entered.get_future().wait();
    worker.enqueue(packet(1));worker.enqueue(packet(2));
    rejects([&]{worker.enqueue(packet(3));}); // blocked encoder cannot block producer
    state.release.set_value();worker.finish();worker.finish();
    check(state.seen==std::vector<std::int64_t>({0,1,2}) && state.finalized && state.destroyed);
    check(worker.meter().peak==.5f);rejects([&]{worker.enqueue(packet(4));});
    rejects([]{OutputWorker bad([]()->std::unique_ptr<OutputSink>{throw std::runtime_error("Initialization failed");});});
    State failure;failure.fail=true;
    OutputWorker failing([&]{return std::make_unique<Sink>(failure);});
    failing.enqueue(packet(0));failure.entered.get_future().wait();failure.release.set_value();
    rejects([&]{failing.finish();});rejects([&]{failing.enqueue(packet(1));});
    check(!failure.finalized && failure.destroyed);
    std::cout<<"PASS: nonblocking bounded queue, FIFO drain, thread affinity, error propagation, finalization\n";
}
