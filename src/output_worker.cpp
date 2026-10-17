#include "output_worker.hpp"
#include <cmath>
#include <stdexcept>
namespace vision {
OutputWorker::OutputWorker(std::function<std::unique_ptr<OutputSink>()> factory,std::size_t capacity):capacity_(capacity) {
    if(!factory || !capacity || capacity>120) throw std::invalid_argument("Invalid output worker configuration");
    worker_=std::thread([this,factory=std::move(factory)]() mutable {run(std::move(factory));});
    std::unique_lock lock(mutex_);changed_.wait(lock,[this]{return ready_;});
    if(error_) {auto error=error_;lock.unlock();worker_.join();std::rethrow_exception(error);}
}
OutputWorker::~OutputWorker() {try {finish();}catch(...) {}}
void OutputWorker::enqueue(OutputPacket packet) {
    if(!packet.frame || packet.frame_number<0 || packet.audio_start<0 || !std::isfinite(packet.gain) || packet.gain<0) throw std::invalid_argument("Invalid output packet");
    std::lock_guard lock(mutex_);
    if(error_) std::rethrow_exception(error_);
    if(closing_) throw std::logic_error("Output is closing");
    if(queue_.size()==capacity_) throw std::runtime_error("Recording cannot keep up: output queue is full");
    queue_.push_back(std::move(packet));changed_.notify_one();
}
Meter OutputWorker::meter() const {
    std::lock_guard lock(mutex_);if(error_) std::rethrow_exception(error_);return meter_;
}
void OutputWorker::finish() {
    {std::lock_guard lock(mutex_);closing_=true;}changed_.notify_all();
    if(worker_.joinable()) worker_.join();
    std::lock_guard lock(mutex_);if(error_) std::rethrow_exception(error_);
}
void OutputWorker::run(std::function<std::unique_ptr<OutputSink>()> factory) {
    try {
        auto sink=factory();if(!sink) throw std::runtime_error("Output factory returned no sink");
        {std::lock_guard lock(mutex_);ready_=true;}changed_.notify_all();
        for(;;) {
            OutputPacket packet;
            {std::unique_lock lock(mutex_);changed_.wait(lock,[this]{return closing_ || !queue_.empty();});
                if(queue_.empty()) break;
                packet=std::move(queue_.front());queue_.pop_front();}
            auto value=sink->write(packet);
            {std::lock_guard lock(mutex_);meter_=value;}
        }
        sink->finish();
    } catch(...) {
        {std::lock_guard lock(mutex_);error_=std::current_exception();closing_=true;ready_=true;queue_.clear();}
        changed_.notify_all();
    }
}
}
