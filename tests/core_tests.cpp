#include "core.hpp"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace vision;
void check(bool ok) { if(!ok) throw std::runtime_error("Contract failed"); }
void near(float a,float b) { check(std::abs(a-b)<0.0001f); }
template<class F> void rejects(F f) {bool rejected=false;try{f();}catch(const std::exception&){rejected=true;}check(rejected);}
std::shared_ptr<Scene> solid(Pixel p) {
    auto s=std::make_shared<Scene>();
    s->add({"background",std::make_shared<StillSource>(Frame(2,2,p)),0,0,2,2,{}});return s;
}
int main() {
    auto red=solid({1,0,0,1}); auto blue=solid({0,0,1,1});
    // Real pixel composition: alpha, order, visibility, crop, scale, offscreen bounds.
    red->add({"overlay",std::make_shared<StillSource>(Frame(1,1,{0,0,1,.5f})),0,0,1,1,{}});
    auto f=red->render(2,2,0);near(f.at(0,0).r,.5f);near(f.at(0,0).b,.5f);near(f.at(1,1).r,1);
    red->move("overlay",0);near(red->render(2,2,0).at(0,0).r,1);
    red->item("background").visible=false;near(red->render(2,2,0).at(0,0).a,.5f);
    red->remove("overlay");red->item("background").visible=true;
    rejects([&]{red->add(red->item("background"));});
    Frame stripe(2,1);stripe.at(0,0)={1,0,0,1};stripe.at(1,0)={0,1,0,1};
    Scene crop;crop.add({"s",std::make_shared<StillSource>(stripe),-1,0,3,1,{1,0,0,0}});
    f=crop.render(2,1,0);near(f.at(0,0).g,1);near(f.at(1,0).g,1);
    crop.item("s").crop.right=1;rejects([&]{crop.render(2,1,0);});
    // Edits are transactional, including hidden layers and extreme crop values.
    crop.item("s").crop.right=0;
    crop.transform("s",1,0,1,1,{0,0,1,0},.25f,0);
    f=crop.render(2,1,0);near(f.at(0,0).a,0);near(f.at(1,0).r,1);near(f.at(1,0).a,.25f);
    crop.item("s").visible=false;
    rejects([&]{crop.transform("s",0,0,0,1,{},1,0);});
    rejects([&]{crop.transform("s",0,0,1,1,{std::numeric_limits<int>::max(),0,1,0},1,0);});
    rejects([&]{crop.transform("s",0,0,1,1,{},std::numeric_limits<float>::quiet_NaN(),0);});
    check(crop.item("s").x==1 && crop.item("s").crop.right==1);
    near(crop.item("s").opacity,.25f);
    // Fade endpoints, midpoint, interruption continuity, cut, invalid clock.
    Switcher sw(2,2,red);sw.take(blue,0,100);
    near(sw.render(0).at(0,0).r,1);f=sw.render(50);near(f.at(0,0).r,.5f);near(f.at(0,0).b,.5f);
    auto green=solid({0,1,0,1});sw.take(green,50,100);
    near(sw.render(50).at(0,0).r,.5f);near(sw.render(100).at(0,0).g,.5f);
    near(sw.render(150).at(0,0).g,1);sw.take(red,150,0);near(sw.render(150).at(0,0).r,1);
    rejects([&]{sw.render(149);});
    // Timestamp-aligned mixing, silence gaps, gain, mute, clipping and meters.
    AudioBlock a{10,1,{.2f,.4f,.6f,.8f}},b{12,1,{.5f,.5f}};
    auto m=mix(11,4,1,{{&a,1,false},{&b,1,false}});
    near(m.block.samples[0],.4f);near(m.block.samples[1],1);near(m.block.samples[2],1);near(m.block.samples[3],0);
    near(m.meter.peak,1);near(m.meter.rms,std::sqrt(.54f));
    m=mix(10,4,1,{{&a,.5f,false},{&b,1,true}});near(m.block.samples[3],.4f);
    AudioBlock stereo{0,2,{.2f,-.2f,.8f,-.8f}};
    m=mix(0,2,2,{{&stereo,1,false}});near(m.block.samples[3],-.8f);
    rejects([&]{mix(0,2,1,{{&stereo,1,false}});});
    a.samples[0]=std::numeric_limits<float>::quiet_NaN();rejects([&]{mix(10,4,1,{{&a,1,false}});});
    std::cout<<"PASS: composition, crop, layer order, fade/cut, interrupted transitions, audio alignment/mute/gain/meters\n";
}
