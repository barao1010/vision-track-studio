#include "video_scale.hpp"
#include <cmath>
#include <algorithm>
#include <iostream>
#include <stdexcept>
using namespace vision;
void check(bool condition) {if(!condition) throw std::runtime_error("Video scaling contract failed");}
bool near(float a,float b) {return std::abs(a-b)<.00001f;}
int main() {
    Frame f(2,2);f.at(0,0)={1,0,0,1};f.at(1,0)={0,1,0,1};f.at(0,1)={0,0,1,1};f.at(1,1)={1,1,1,1};
    auto identity=scale_frame(f,2,2);check(identity.at(1,0).g==1 && identity.at(0,1).b==1);
    auto larger=scale_frame(f,3,3);auto center=larger.at(1,1);check(near(center.r,.5f)&&near(center.g,.5f)&&near(center.b,.5f)&&center.a==1);
    check(larger.at(0,0).r==1 && larger.at(2,0).g==1 && larger.at(0,2).b==1);
    auto smaller=scale_frame(f,1,1);check(near(smaller.at(0,0).r,.5f));
    Frame edge(2,1);edge.at(0,0)={1,0,0,1};edge.at(1,0)={0,0,1,0};
    auto blended=scale_frame(edge,3,1).at(1,0);check(near(blended.a,.5f)&&blended.r==1&&blended.b==0);
    auto transparent=scale_frame(Frame(1,1,{1,1,1,0}),2,2).at(0,0);check(transparent.a==0&&transparent.r==0);
    for(int height:{360,720,1080}) {auto solid=scale_frame(Frame(1,1,{.2f,.3f,.4f,1}),height*16/9,height);check(near(solid.at(solid.width()-1,height-1).g,.3f));}
    // Independent four-tap oracle for both up/down scaling and varying alpha.
    Frame pattern(7,5);
    for(int y=0;y<5;++y) for(int x=0;x<7;++x) pattern.at(x,y)={x/6.f,y/4.f,((x*13+y*7)%17)/16.f,((x+y*3)%9)/8.f};
    for(int w:{1,3,11}) for(int h:{1,2,13}) {
        auto actual=scale_frame(pattern,w,h);
        for(int y=0;y<h;++y) for(int x=0;x<w;++x) {
            double sx=std::clamp((x+.5)*7/w-.5,0.,6.),sy=std::clamp((y+.5)*5/h-.5,0.,4.);
            int x0=static_cast<int>(sx),y0=static_cast<int>(sy);float fx=static_cast<float>(sx-x0),fy=static_cast<float>(sy-y0);
            Pixel expected{};
            for(int dy=0;dy<2;++dy) for(int dx=0;dx<2;++dx) {
                auto p=pattern.at(std::min(x0+dx,6),std::min(y0+dy,4));float weight=(dx?fx:1-fx)*(dy?fy:1-fy)*p.a;
                expected.r+=weight*p.r;expected.g+=weight*p.g;expected.b+=weight*p.b;expected.a+=weight;
            }
            if(expected.a>0) {expected.r/=expected.a;expected.g/=expected.a;expected.b/=expected.a;}
            auto p=actual.at(x,y);check(near(p.r,expected.r)&&near(p.g,expected.g)&&near(p.b,expected.b)&&near(p.a,expected.a));
        }
    }
    bool rejected=false;try {scale_frame(f,0,5);}catch(const std::invalid_argument&) {rejected=true;}check(rejected);
    std::cout<<"PASS: linear scaling, orientation, alpha edges, identity and output sizes\n";
}
