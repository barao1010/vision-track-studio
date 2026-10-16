#include "media.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace vision {
namespace {
float linear(unsigned char v) {float s=static_cast<float>(v)/255;return s<=.04045f?s/12.92f:std::pow((s+.055f)/1.055f,2.4f);}
unsigned char srgb(float l) {
    if(!std::isfinite(l)) throw std::invalid_argument("Nonfinite pixel");
    l=std::clamp(l,0.f,1.f);
    float s=l<=.0031308f?12.92f*l:1.055f*std::pow(l,1.f/2.4f)-.055f;
    return static_cast<unsigned char>(std::lround(s*255));
}
std::string token(std::istream& in) {
    std::string result;
    while(in) { in>>std::ws; if(in.peek()!='#') break;in.ignore(std::numeric_limits<std::streamsize>::max(),'\n'); }
    if(!(in>>result)) throw std::runtime_error("Truncated PPM header");
    return result;
}
int integer(const std::string& s) {
    std::size_t end=0;int n=std::stoi(s,&end);
    if(end!=s.size()) throw std::runtime_error("Invalid PPM integer");
    return n;
}
}
Frame read_ppm(const std::filesystem::path& path) {
    std::ifstream file(path,std::ios::binary);
    if(token(file)!="P6") throw std::runtime_error("Only P6 PPM is supported");
    int w=integer(token(file)),h=integer(token(file));
    if(integer(token(file))!=255) throw std::runtime_error("Only 8-bit PPM supported");
    const int delimiter=file.get();
    if(delimiter!=' ' && delimiter!='\n' && delimiter!='\r' && delimiter!='\t') throw std::runtime_error("Invalid PPM delimiter");
    if(delimiter=='\r' && file.peek()=='\n') file.get();
    Frame result(w,h);
    for(int y=0;y<h;++y) for(int x=0;x<w;++x) {
        unsigned char rgb[3];
        if(!file.read(reinterpret_cast<char*>(rgb),3)) throw std::runtime_error("Truncated PPM raster");
        result.at(x,y)={linear(rgb[0]),linear(rgb[1]),linear(rgb[2]),1};
    }
    return result;
}
RawRecorder::RawRecorder(const std::filesystem::path& dir,int w,int h,int fps,int rate)
    :width_(w),height_(h),fps_(fps),rate_(rate) {
    if(w<=0 || h<=0 || fps<=0 || fps>240 || rate<8000 || rate>192000) throw std::invalid_argument("Invalid recording format");
    if(std::filesystem::exists(dir)) throw std::runtime_error("Output directory already exists");
    std::filesystem::create_directories(dir);
    video_.exceptions(std::ios::failbit|std::ios::badbit);audio_.exceptions(std::ios::failbit|std::ios::badbit);manifest_.exceptions(std::ios::failbit|std::ios::badbit);
    video_.open(dir/"video.rgb",std::ios::binary);audio_.open(dir/"audio.f32le",std::ios::binary);manifest_.open(dir/"recording.json");
}
void RawRecorder::append(const Frame& frame,const AudioBlock& block) {
    if(finished_) throw std::logic_error("Recorder finalized");
    const auto next=(frames_+1)*rate_/fps_;
    if(frame.width()!=width_ || frame.height()!=height_ || block.channels!=2 || block.start_sample!=samples_ || block.samples.size()!=static_cast<std::size_t>(next-samples_)*2)
        throw std::invalid_argument("Video/audio timeline mismatch");
    std::vector<unsigned char> bytes;bytes.reserve(static_cast<std::size_t>(width_)*height_*3);
    for(int y=0;y<height_;++y) for(int x=0;x<width_;++x) {
        const auto p=frame.at(x,y);
        if(!std::isfinite(p.a)) throw std::invalid_argument("Invalid alpha");
        const float alpha=std::clamp(p.a,0.f,1.f);
        bytes.push_back(srgb(p.r*alpha));bytes.push_back(srgb(p.g*alpha));bytes.push_back(srgb(p.b*alpha));
    }
    for(float v:block.samples) if(!std::isfinite(v)) throw std::invalid_argument("Invalid audio sample");
    video_.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));
    for(float v:block.samples) {
        const auto bits=std::bit_cast<std::uint32_t>(v);
        for(int shift=0;shift<32;shift+=8) audio_.put(static_cast<char>((bits>>shift)&255));
    }
    ++frames_;samples_=next;
}
void RawRecorder::finish() {
    if(finished_) return;
    video_.close();audio_.close();
    manifest_<<"{\"width\":"<<width_<<",\"height\":"<<height_<<",\"fps\":"<<fps_<<",\"sample_rate\":"<<rate_<<",\"channels\":2,\"frames\":"<<frames_<<",\"samples\":"<<samples_<<"}\n";
    manifest_.close();finished_=true;
}
}
