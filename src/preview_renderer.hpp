#pragma once
#include "core.hpp"
#include <condition_variable>
#include <exception>
#include <mutex>
#include <optional>
#include <thread>
namespace vision {
// Capture stays on the caller's thread (including STA-only browser sources).
// Only frozen CPU frames cross to the composition worker. One pending request
// replaces older pending work; latest() never waits for a render to finish.
class PreviewRenderer {
public:
    PreviewRenderer();
    ~PreviewRenderer();
    PreviewRenderer(const PreviewRenderer&)=delete;
    PreviewRenderer& operator=(const PreviewRenderer&)=delete;
    std::uint64_t update(const Scene& scene,int canvas_width,int canvas_height,
                         std::int64_t timestamp,int preview_width=320,int preview_height=180);
    struct Result {std::uint64_t serial=0;std::shared_ptr<const Frame> frame;};
    Result latest() const;
private:
    struct Request {Scene scene;int width,height,preview_width,preview_height;std::int64_t timestamp;std::uint64_t serial;};
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
