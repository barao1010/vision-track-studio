#include "scheduled_output.hpp"
#include "audio_buffer.hpp"
#include "recording_rate.hpp"
#include <chrono>
#include <cmath>
#include <stdexcept>
namespace vision {
namespace {
void valid(const std::shared_ptr<const Frame>& frame,float gain) {
    if(!frame || !std::isfinite(gain) || gain<0) throw std::invalid_argument("Invalid scheduled output snapshot");
}
}
ScheduledOutput::ScheduledOutput(std::function<std::unique_ptr<OutputSink>()> factory,
                                 std::shared_ptr<const Frame> frame,float gain,bool muted,int fps):fps_(fps) {
    recording_audio_frames(fps);valid(frame,gain);if(!factory) throw std::invalid_argument("Missing output factory");
    latest_={std::move(frame),0,0,gain,muted};
    worker_=std::thread([this,factory=std::move(factory)]() mutable {run(std::move(factory));});
    std::unique_lock lock(mutex_);changed_.wait(lock,[this]{return ready_;});
    if(error_) {auto error=error_;lock.unlock();worker_.join();std::rethrow_exception(error);}
}
ScheduledOutput::~ScheduledOutput() {try {finish();}catch(...) {}}
void ScheduledOutput::update(std::shared_ptr<const Frame> frame,float gain,bool muted) {
    valid(frame,gain);std::lock_guard lock(mutex_);
    if(error_) std::rethrow_exception(error_);
    if(closing_) throw std::logic_error("Output is closing");
    latest_.frame=std::move(frame);latest_.gain=gain;latest_.muted=muted;
}
Meter ScheduledOutput::meter() const {
    std::lock_guard lock(mutex_);if(error_) std::rethrow_exception(error_);return meter_;
}
void ScheduledOutput::finish() {
    {std::lock_guard lock(mutex_);closing_=true;}changed_.notify_all();
    if(worker_.joinable()) worker_.join();
    std::lock_guard lock(mutex_);if(error_) std::rethrow_exception(error_);
}
void ScheduledOutput::run(std::function<std::unique_ptr<OutputSink>()> factory) {
    try {
        auto sink=factory();if(!sink) throw std::runtime_error("Output factory returned no sink");
        using Clock=std::chrono::steady_clock;
        const auto start=Clock::now();
        const auto audioStart=audio_sample_time(std::chrono::duration_cast<std::chrono::nanoseconds>(start.time_since_epoch()).count());
        for(std::int64_t index=0;;++index) {
            // Split quotient/remainder avoids multiplication overflow in long sessions.
            const auto deadline=start+std::chrono::seconds(index/fps_)+std::chrono::nanoseconds((index%fps_)*1000000000/fps_);
            OutputPacket packet;
            {
                std::unique_lock lock(mutex_);
                changed_.wait_until(lock,deadline,[this]{return closing_;});
                if(closing_) break;
                if(Clock::now()-deadline>std::chrono::seconds(10)) throw std::runtime_error("Recording stopped: encoder more than ten seconds behind");
                packet=latest_;
            }
            packet.frame_number=index;packet.audio_start=audioStart+index*recording_audio_frames(fps_);
            auto meter=sink->write(packet);
            {std::lock_guard lock(mutex_);meter_=meter;ready_=true;}
            changed_.notify_all();
        }
        sink->finish();
    } catch(...) {
        {std::lock_guard lock(mutex_);error_=std::current_exception();closing_=true;ready_=true;}
        changed_.notify_all();
    }
}
}
