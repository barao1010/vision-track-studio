#include "video_pack.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
namespace vision {
namespace {
const std::array<std::uint8_t,65536>& transfer() {
    static const auto table=[] {
        std::array<std::uint8_t,65536> result{};
        for(std::size_t i=0;i<result.size();++i) {
            const double value=static_cast<double>(i)/65535;
            result[i]=static_cast<std::uint8_t>(std::lround(255*(value<=.0031308?12.92*value:1.055*std::pow(value,1/2.4)-.055)));
        }
        return result;
    }();
    return table;
}
std::uint8_t encode(float linear,const std::array<std::uint8_t,65536>& table) {
    const auto index=static_cast<std::size_t>(std::clamp(linear,0.f,1.f)*65535.f+.5f);
    return table[index];
}
}
std::uint8_t linear_to_srgb8(float linear) {
    if(!std::isfinite(linear)) throw std::invalid_argument("Nonfinite pixel");
    return encode(linear,transfer());
}
std::vector<std::uint8_t> pack_bgrx(const Frame& frame) {
    const auto& table=transfer();
    std::vector<std::uint8_t> bytes(static_cast<std::size_t>(frame.width())*frame.height()*4);
    for(int y=0;y<frame.height();++y) for(int x=0;x<frame.width();++x) {
        const auto p=frame.at(x,y);
        if(!std::isfinite(p.r)||!std::isfinite(p.g)||!std::isfinite(p.b)||!std::isfinite(p.a)) throw std::invalid_argument("Nonfinite pixel");
        const auto alpha=std::clamp(p.a,0.f,1.f);
        const auto offset=(static_cast<std::size_t>(y)*frame.width()+x)*4;
        bytes[offset]=encode(p.b*alpha,table);bytes[offset+1]=encode(p.g*alpha,table);bytes[offset+2]=encode(p.r*alpha,table);
    }
    return bytes;
}
}
