#pragma once
#include "core.hpp"
#include <condition_variable>
#include <deque>
#include <exception>
#include <functional>
#include <mutex>
#include <thread>
namespace vision {
struct OutputPacket {
    std::shared_ptr<const Frame> frame;
    std::int64_t frame_number=0, audio_start=0;
    float gain=1;
    bool muted=false;
};
class OutputSink {
public:
    virtual ~OutputSink()=default;
    virtual Meter write(const OutputPacket& packet)=0;
    virtual void finish()=0;
};
// One producer. Factory, sink writes, finalization and destruction all run on
// the same worker thread. Enqueue never waits for encoding or queue space.
class OutputWorker {
public:
    explicit OutputWorker(std::function<std::unique_ptr<OutputSink>()> factory,std::size_t capacity=8);
    ~OutputWorker();
    OutputWorker(const OutputWorker&)=delete;
    OutputWorker& operator=(const OutputWorker&)=delete;
    void enqueue(OutputPacket packet);
    Meter meter() const;
    void finish(); // stop accepting, drain FIFO, finalize, propagate failure
private:
    void run(std::function<std::unique_ptr<OutputSink>()> factory);
    mutable std::mutex mutex_;
    std::condition_variable changed_;
    std::deque<OutputPacket> queue_;
    std::thread worker_;
    std::size_t capacity_;
    bool ready_=false,closing_=false;
    std::exception_ptr error_;
    Meter meter_;
};
}
