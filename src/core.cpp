#include "core.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace vision {
namespace {
void require(bool ok, const char* message) { if (!ok) throw std::invalid_argument(message); }
Pixel over(Pixel s, Pixel d, float opacity) {
    const float sa=std::clamp(s.a*opacity,0.f,1.f), da=std::clamp(d.a,0.f,1.f);
    const float a=sa+da*(1-sa);
    if (a==0) return {};
    return {(s.r*sa+d.r*da*(1-sa))/a, (s.g*sa+d.g*da*(1-sa))/a,
            (s.b*sa+d.b*da*(1-sa))/a,a};
}
Pixel blend(Pixel a, Pixel b, float t) {
    const float alpha=a.a*(1-t)+b.a*t;
    if (alpha==0) return {};
    return {(a.r*a.a*(1-t)+b.r*b.a*t)/alpha,
            (a.g*a.a*(1-t)+b.g*b.a*t)/alpha,
            (a.b*a.a*(1-t)+b.b*b.a*t)/alpha,alpha};
}
}
Frame::Frame(int w,int h,Pixel p):width_(w),height_(h) {
    require(w>0 && h>0 && w<=16384 && h<=16384,"Invalid frame dimensions");
    pixels_.assign(static_cast<std::size_t>(w)*h,p);
}
Pixel& Frame::at(int x,int y) {
    if(x<0 || y<0 || x>=width_ || y>=height_) throw std::out_of_range("Pixel");
    return pixels_[static_cast<std::size_t>(y)*width_+x];
}
const Pixel& Frame::at(int x,int y) const { return const_cast<Frame*>(this)->at(x,y); }
Item& Scene::item(const std::string& id) {
    auto it=std::find_if(items_.begin(),items_.end(),[&](auto& i){return i.id==id;});
    if(it==items_.end()) throw std::out_of_range("Unknown scene item");
    return *it;
}
void Scene::add(Item i) {
    require(!i.id.empty() && i.source!=nullptr,"Item needs identity and source");
    require(std::none_of(items_.begin(),items_.end(),[&](auto& v){return v.id==i.id;}),"Duplicate item");
    items_.push_back(std::move(i));
}
void Scene::remove(const std::string& id) {
    item(id);
    std::erase_if(items_,[&](auto& i){return i.id==id;});
}
void Scene::move(const std::string& id,std::size_t position) {
    require(position<items_.size(),"Layer outside scene");
    Item copy=item(id); remove(id);
    items_.insert(items_.begin()+static_cast<std::ptrdiff_t>(position),std::move(copy));
}
Frame Scene::render(int w,int h,std::int64_t time) const {
    Frame result(w,h);
    for(const auto& i:items_) {
        if(!i.visible) continue;
        require(i.source && i.width>0 && i.height>0,"Invalid item transform");
        require(std::isfinite(i.opacity) && i.opacity>=0 && i.opacity<=1,"Invalid opacity");
        const Frame src=i.source->frame(time);
        const auto c=i.crop;
        require(c.left>=0 && c.top>=0 && c.right>=0 && c.bottom>=0,"Negative crop");
        const auto sw=static_cast<std::int64_t>(src.width())-c.left-c.right;
        const auto sh=static_cast<std::int64_t>(src.height())-c.top-c.bottom;
        require(sw>0 && sh>0,"Crop removes entire source");
        const auto endx=std::min<std::int64_t>(w,static_cast<std::int64_t>(i.x)+i.width);
        const auto endy=std::min<std::int64_t>(h,static_cast<std::int64_t>(i.y)+i.height);
        for(int y=std::max(0,i.y);y<endy;++y) for(int x=std::max(0,i.x);x<endx;++x) {
            const int sx=static_cast<int>(c.left+(static_cast<std::int64_t>(x)-i.x)*sw/i.width);
            const int sy=static_cast<int>(c.top+(static_cast<std::int64_t>(y)-i.y)*sh/i.height);
            result.at(x,y)=over(src.at(sx,sy),result.at(x,y),i.opacity);
        }
    }
    return result;
}
Switcher::Switcher(int w,int h,std::shared_ptr<const Scene> initial):width_(w),height_(h),current_(std::move(initial)) {
    require(current_!=nullptr,"Initial scene required");
    Frame validate(w,h);
}
void Switcher::check_time(std::int64_t t) { require(t>=0 && t>=clock_,"Nonmonotonic clock"); clock_=t; }
void Switcher::take(std::shared_ptr<const Scene> next,std::int64_t now,std::int64_t duration) {
    require(next!=nullptr && duration>=0,"Invalid transition");
    check_time(now);
    if(duration==0) {current_=std::move(next);target_.reset();interrupted_.reset();return;}
    if(target_) interrupted_=std::make_unique<Frame>(render(now));
    target_=std::move(next); start_=now; duration_=duration;
}
Frame Switcher::render(std::int64_t now) {
    check_time(now);
    if(!target_) return current_->render(width_,height_,now);
    const auto elapsed=now-start_;
    if(elapsed>=duration_) {
        current_=std::move(target_); interrupted_.reset();
        return current_->render(width_,height_,now);
    }
    Frame a=interrupted_?*interrupted_:current_->render(width_,height_,now);
    const Frame b=target_->render(width_,height_,now);
    const float t=static_cast<float>(static_cast<double>(elapsed)/static_cast<double>(duration_));
    for(int y=0;y<height_;++y) for(int x=0;x<width_;++x) a.at(x,y)=blend(a.at(x,y),b.at(x,y),t);
    return a;
}
MixedAudio mix(std::int64_t start,std::size_t frames,int channels,const std::vector<AudioInput>& inputs) {
    require(start>=0 && (channels==1 || channels==2) && frames<=192000,"Invalid audio interval");
    require(start<=std::numeric_limits<std::int64_t>::max()-static_cast<std::int64_t>(frames),"Audio timestamp overflow");
    MixedAudio out{{start,channels,std::vector<float>(frames*channels,0)}, {}};
    for(const auto& input:inputs) {
        require(std::isfinite(input.gain) && input.gain>=0,"Invalid gain");
        if(!input.block || input.muted) continue;
        const auto& b=*input.block;
        require(b.channels==channels && b.samples.size()%channels==0 && b.start_sample>=0,"Invalid audio block");
        require(b.samples.size()/channels<=static_cast<std::size_t>(std::numeric_limits<std::int64_t>::max()-b.start_sample),"Block overflow");
        const auto begin=std::max(start,b.start_sample);
        const auto end=std::min(start+static_cast<std::int64_t>(frames),b.start_sample+static_cast<std::int64_t>(b.samples.size()/channels));
        for(auto f=begin;f<end;++f) for(int ch=0;ch<channels;++ch) {
            const float value=b.samples[static_cast<std::size_t>(f-b.start_sample)*channels+ch];
            require(std::isfinite(value),"Nonfinite audio sample");
            auto& destination=out.block.samples[static_cast<std::size_t>(f-start)*channels+ch];
            destination+=value*input.gain;
            require(std::isfinite(destination),"Audio overflow");
        }
    }
    double energy=0;
    for(float& value:out.block.samples) {
        value=std::clamp(value,-1.f,1.f);
        out.meter.peak=std::max(out.meter.peak,std::abs(value));energy+=static_cast<double>(value)*value;
    }
    if(!out.block.samples.empty()) out.meter.rms=static_cast<float>(std::sqrt(energy/out.block.samples.size()));
    return out;
}
}
