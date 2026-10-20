#include "program_renderer.hpp"
#include <stdexcept>
#include <utility>

namespace vision {
ProgramRenderer::ProgramRenderer():worker_([this]{run();}) {}
ProgramRenderer::~ProgramRenderer() {
    {
        std::lock_guard lock(mutex_);
        closing_=true;
        pending_.reset();
    }
    changed_.notify_all();
    if(worker_.joinable()) worker_.join();
}
std::uint64_t ProgramRenderer::update(Switcher& switcher,std::int64_t timestamp) {
    auto compose=switcher.snapshot(timestamp);
    std::uint64_t serial=0;
    {
        std::lock_guard lock(mutex_);
        if(error_) std::rethrow_exception(error_);
        if(closing_) throw std::runtime_error("Program renderer is closing");
        serial=++serial_;
        pending_=Request{std::move(compose),serial};
    }
    changed_.notify_one();
    return serial;
}
ProgramRenderer::Result ProgramRenderer::latest() const {
    std::lock_guard lock(mutex_);
    if(error_) std::rethrow_exception(error_);
    return result_;
}
void ProgramRenderer::run() {
    try {
        for(;;) {
            std::optional<Request> request;
            {
                std::unique_lock lock(mutex_);
                changed_.wait(lock,[this]{return closing_ || pending_.has_value();});
                if(closing_) return;
                request=std::move(pending_);
                pending_.reset();
            }
            auto frame=std::make_shared<Frame>(request->compose());
            {
                std::lock_guard lock(mutex_);
                if(!result_.frame || request->serial>result_.serial)
                    result_={request->serial,std::move(frame)};
            }
        }
    } catch(...) {
        std::lock_guard lock(mutex_);
        error_=std::current_exception();
        pending_.reset();
    }
}
}
