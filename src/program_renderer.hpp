#pragma once
#include "core.hpp"
#include <condition_variable>
#include <exception>
#include <functional>
#include <mutex>
#include <optional>
#include <thread>

namespace vision {
// Program composition runs away from the window thread. Switcher::snapshot
// captures all live source frames first, preserving STA/device thread affinity.
// At most one pending task is retained; newer program states replace stale work.
class ProgramRenderer {
public:
    ProgramRenderer();
    ~ProgramRenderer();
    ProgramRenderer(const ProgramRenderer&)=delete;
    ProgramRenderer& operator=(const ProgramRenderer&)=delete;

    std::uint64_t update(Switcher& switcher,std::int64_t timestamp_ns);
    struct Result {
        std::uint64_t serial=0;
        std::shared_ptr<const Frame> frame;
    };
    Result latest() const;

private:
    struct Request {
        std::function<Frame()> compose;
        std::uint64_t serial=0;
    };
    mutable std::mutex mutex_;
    std::condition_variable changed_;
    std::optional<Request> pending_;
    Result result_;
    std::exception_ptr error_;
    std::uint64_t serial_=0;
    bool closing_=false;
    std::thread worker_;
    void run();
};
}
