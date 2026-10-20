#include "preview_renderer.hpp"
#include <chrono>
#include <iostream>
#include <stdexcept>
using namespace vision;
void check(bool ok) {if(!ok) throw std::runtime_error("Preview renderer contract failed");}
template<class F> void rejects(F fn) {bool caught=false;try {fn();}catch(const std::exception&) {caught=true;}check(caught);}
struct Source:VideoSource {
    std::thread::id owner=std::this_thread::get_id();
    mutable int calls=0;
    Pixel pixel{1,0,0,1};
    bool fail=false;
    Frame frame(std::int64_t) const override {
        check(std::this_thread::get_id()==owner);++calls;
        if(fail) throw std::runtime_error("Capture failed");
        return Frame(2,2,pixel);
    }
};
PreviewRenderer::Result await(PreviewRenderer& renderer,std::uint64_t serial) {
    auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(5);
    do {auto r=renderer.latest();if(r.serial==serial) return r;std::this_thread::sleep_for(std::chrono::milliseconds(2));}
    while(std::chrono::steady_clock::now()<deadline);
    throw std::runtime_error("Preview did not publish latest request");
}
int main() {
    auto source=std::make_shared<Source>();auto hidden=std::make_shared<Source>();hidden->fail=true;
    Scene scene;scene.add({"a",source,0,0,2,2,{}});scene.add({"b",source,2,0,2,2,{}});
    scene.add({"hidden",hidden,0,0,4,2,{},1,false});
    auto frozen=scene.snapshot(0);check(source->calls==1 && hidden->calls==0);
    source->pixel={0,1,0,1};scene.item("a").x=1;
    auto pixels=frozen.render(4,2,0);check(pixels.at(0,0).r==1 && pixels.at(3,0).r==1 && source->calls==1);
    PreviewRenderer renderer;
    auto serial=renderer.update(scene,4,2,0,4,2);
    source->pixel={0,0,1,1};scene.item("a").visible=false;
    auto first=await(renderer,serial);check(first.frame->at(1,0).g==1 && first.frame->at(3,0).g==1);
    // Replace pending requests rapidly; the final snapshot must arrive, without mutating old results.
    for(int n=0;n<100;++n) serial=renderer.update(scene,640,360,n,320,180);
    auto last=await(renderer,serial);check(last.frame->width()==320 && last.frame->height()==180 && last.frame->at(1,0).b==1);
    check(first.frame->at(3,0).g==1);
    source->fail=true;rejects([&]{renderer.update(scene,4,2,101,4,2);});check(renderer.latest().serial==serial);
    rejects([&]{renderer.update(scene,0,2,102);});
    // Composition failure on the worker is surfaced; shutdown remains joinable.
    source->fail=false;scene.item("b").opacity=2;
    PreviewRenderer failed;failed.update(scene,4,2,103,4,2);
    bool surfaced=false;auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(5);
    while(!surfaced && std::chrono::steady_clock::now()<deadline) {
        try {failed.latest();}catch(const std::exception&) {surfaced=true;}
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    check(surfaced);rejects([&]{failed.update(scene,4,2,104,4,2);});
    std::cout<<"PASS: source thread affinity, shared/hidden capture, immutable preview, newest request, capture/render errors and shutdown\n";
}
