#include "preview_renderer.hpp"
#include "video_scale.hpp"
#include <stdexcept>
namespace vision {
PreviewRenderer::PreviewRenderer():worker_([this]{run();}) {}
PreviewRenderer::~PreviewRenderer() {
    {std::lock_guard lock(mutex_);closing_=true;pending_.reset();}
    changed_.notify_all();worker_.join();
}
std::uint64_t PreviewRenderer::update(const Scene& scene,int w,int h,std::int64_t time,int pw,int ph) {
    if(w<=0 || h<=0 || w>4096 || h>4096 || pw<=0 || ph<=0 || pw>4096 || ph>4096 || time<0)
        throw std::invalid_argument("Invalid preview dimensions or timestamp");
    // Source access is deliberately outside the worker and before publication.
    auto snapshot=scene.snapshot(time);
    std::uint64_t serial;
    {std::lock_guard lock(mutex_);
        if(error_) std::rethrow_exception(error_);
        serial=++serial_;
        pending_=Request{std::move(snapshot),w,h,pw,ph,time,serial};
    }
    changed_.notify_one();return serial;
}
PreviewRenderer::Result PreviewRenderer::latest() const {
    std::lock_guard lock(mutex_);if(error_) std::rethrow_exception(error_);return result_;
}
void PreviewRenderer::run() {
    try {
        for(;;) {
            std::optional<Request> request;
            {std::unique_lock lock(mutex_);changed_.wait(lock,[this]{return closing_ || pending_.has_value();});
                if(closing_) return;
                request=std::move(pending_);pending_.reset();
            }
            auto frame=request->scene.render(request->width,request->height,request->timestamp);
            if(frame.width()!=request->preview_width || frame.height()!=request->preview_height)
                frame=scale_frame(frame,request->preview_width,request->preview_height);
            auto ready=std::make_shared<Frame>(std::move(frame));
            {std::lock_guard lock(mutex_);result_={request->serial,std::move(ready)};}
        }
    }catch(...) {std::lock_guard lock(mutex_);error_=std::current_exception();pending_.reset();}
}
}
