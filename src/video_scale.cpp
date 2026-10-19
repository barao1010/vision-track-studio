#include "video_scale.hpp"
#include <algorithm>
#include <array>
#include <stdexcept>
namespace vision {
Frame scale_frame(const Frame& source,int width,int height) {
    if(width<1 || height<1 || width>4096 || height>4096) throw std::invalid_argument("Invalid scaled frame dimensions");
    if(width==source.width() && height==source.height()) return source;
    struct Column {int left,right;float weight;};
    std::vector<Column> columns;columns.reserve(width);
    for(int x=0;x<width;++x) {
        const double sx=std::clamp((x+.5)*source.width()/width-.5,0.,double(source.width()-1));
        const int left=static_cast<int>(sx);
        columns.push_back({left,std::min(left+1,source.width()-1),static_cast<float>(sx-left)});
    }
    struct CachedRow {int index=-1;std::vector<Pixel> pixels;};
    std::array<CachedRow,2> cache;
    for(auto& row:cache) row.pixels.resize(width);
    auto horizontal=[&](int y,int protectedRow)->const std::vector<Pixel>& {
        for(auto& row:cache) if(row.index==y) return row.pixels;
        auto& target=cache[cache[0].index==protectedRow?1:0];
        auto input=source.row(y);
        for(int x=0;x<width;++x) {
            const auto c=columns[x];const auto l=input[c.left],r=input[c.right];
            const float la=l.a*(1-c.weight),ra=r.a*c.weight;
            target.pixels[x]={l.r*la+r.r*ra,l.g*la+r.g*ra,l.b*la+r.b*ra,la+ra};
        }
        target.index=y;return target.pixels;
    };
    Frame result(width,height);
    for(int y=0;y<height;++y) {
        const double sy=std::clamp((y+.5)*source.height()/height-.5,0.,double(source.height()-1));
        const int y0=static_cast<int>(sy),y1=std::min(y0+1,source.height()-1);
        const float fy=static_cast<float>(sy-y0);
        const auto& top=horizontal(y0,-1);
        const auto& bottom=horizontal(y1,y0);
        auto output=result.row(y);
        for(int x=0;x<width;++x) {
            const auto a=top[x],b=bottom[x];
            Pixel out{a.r*(1-fy)+b.r*fy,a.g*(1-fy)+b.g*fy,a.b*(1-fy)+b.b*fy,a.a*(1-fy)+b.a*fy};
            if(out.a>0) {out.r/=out.a;out.g/=out.a;out.b/=out.a;}
            output[x]=out;
        }
    }
    return result;
}
}
