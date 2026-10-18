#include "video_scale.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace vision {
Frame scale_frame(const Frame& source,int width,int height) {
    if(width<1 || height<1 || width>4096 || height>4096) throw std::invalid_argument("Invalid scaled frame dimensions");
    if(width==source.width() && height==source.height()) return source;
    Frame result(width,height);
    for(int y=0;y<height;++y) {
        const double sy=std::clamp((y+.5)*source.height()/height-.5,0.,double(source.height()-1));
        const int y0=static_cast<int>(sy),y1=std::min(y0+1,source.height()-1);
        const float fy=static_cast<float>(sy-y0);
        for(int x=0;x<width;++x) {
            const double sx=std::clamp((x+.5)*source.width()/width-.5,0.,double(source.width()-1));
            const int x0=static_cast<int>(sx),x1=std::min(x0+1,source.width()-1);
            const float fx=static_cast<float>(sx-x0);
            const Pixel pixels[]={source.at(x0,y0),source.at(x1,y0),source.at(x0,y1),source.at(x1,y1)};
            const float weights[]={(1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy};
            Pixel out{};
            for(int i=0;i<4;++i) {const auto weight=weights[i]*pixels[i].a;out.a+=weight;out.r+=weight*pixels[i].r;out.g+=weight*pixels[i].g;out.b+=weight*pixels[i].b;}
            if(out.a>0) {out.r/=out.a;out.g/=out.a;out.b/=out.a;}
            result.at(x,y)=out;
        }
    }
    return result;
}
}
