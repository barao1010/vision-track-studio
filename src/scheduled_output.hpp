#pragma once
#include "output_worker.hpp"
namespace vision {
// Fixed 30 fps / 48 kHz output clock, independent of UI repaint frequency.
// The newest immutable video/control snapshot replaces older unpublished ones.
// Capture/composition remain producer responsibilities.
class ScheduledOutput {
public:
    ScheduledOutput(std::function<std::unique_ptr<OutputSink>()> factory,
                    std::shared_ptr<const Frame> initial,float gain=1,bool muted=false,int fps=30);
    ~ScheduledOutput();
    ScheduledOutput(const ScheduledOutput&)=delete;
    ScheduledOutput& operator=(const ScheduledOutput&)=delete;
    void update(std::shared_ptr<const Frame> frame,float gain,bool muted);
    Meter meter() const;
    void finish();
private:
    void run(std::function<std::unique_ptr<OutputSink>()> factory);
    mutable std::mutex mutex_;
    std::condition_variable changed_;
    std::thread worker_;
    OutputPacket latest_;
    int fps_=30;
    Meter meter_;
    bool ready_=false,closing_=false;
    std::exception_ptr error_;
};
}
