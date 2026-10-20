#include "program_renderer.hpp"
#include <chrono>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <thread>

using namespace vision;
namespace {
void expect(bool value,const char* message) {if(!value) throw std::runtime_error(message);}
class ThreadSource final:public VideoSource {
public:
    explicit ThreadSource(Pixel color):color_(color) {}
    Frame frame(std::int64_t) const override {
        last_thread=std::this_thread::get_id();
        return Frame(1,1,color_);
    }
    mutable std::thread::id last_thread;
private:
    Pixel color_;
};
std::shared_ptr<Scene> scene(Pixel color) {
    auto result=std::make_shared<Scene>();
    result->add({"pixel",std::make_shared<StillSource>(Frame(1,1,color)),0,0,1,1,{}});
    return result;
}
ProgramRenderer::Result waitFor(ProgramRenderer& renderer,std::uint64_t serial) {
    const auto until=std::chrono::steady_clock::now()+std::chrono::seconds(2);
    while(std::chrono::steady_clock::now()<until) {
        auto result=renderer.latest();
        if(result.frame && result.serial>=serial) return result;
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    throw std::runtime_error("Program render timed out");
}
void same(Pixel a,Pixel b,const char* message) {
    if(std::abs(a.r-b.r)>0.0001f || std::abs(a.g-b.g)>0.0001f ||
       std::abs(a.b-b.b)>0.0001f || std::abs(a.a-b.a)>0.0001f)
        throw std::runtime_error(message);
}
}
int main() {
    try {
        const auto caller=std::this_thread::get_id();
        auto tracked=std::make_shared<ThreadSource>(Pixel{1,0,0,1});
        auto firstScene=std::make_shared<Scene>();
        firstScene->add({"live",tracked,0,0,1,1,{}});
        Switcher switcher(1,1,firstScene);
        ProgramRenderer renderer;

        auto serial=renderer.update(switcher,0);
        auto first=waitFor(renderer,serial);
        same(first.frame->at(0,0),{1,0,0,1},"Initial program frame is not red");
        expect(tracked->last_thread==caller,"Live source was sampled away from caller thread");

        auto blue=scene({0,0,1,1});
        switcher.take(blue,1,100);
        serial=renderer.update(switcher,1);
        auto atStart=waitFor(renderer,serial);
        same(atStart.frame->at(0,0),{1,0,0,1},"Fade start must preserve outgoing scene");

        serial=renderer.update(switcher,51);
        auto midpoint=waitFor(renderer,serial);
        same(midpoint.frame->at(0,0),{0.5f,0,0.5f,1},"Program fade midpoint is incorrect");

        auto green=scene({0,1,0,1});
        switcher.take(green,51,100,midpoint.frame.get());
        serial=renderer.update(switcher,51);
        auto interrupted=waitFor(renderer,serial);
        same(interrupted.frame->at(0,0),midpoint.frame->at(0,0),"Interrupted fade jumped at its start");

        std::uint64_t finalSerial=serial;
        for(std::int64_t t=52;t<152;++t) finalSerial=renderer.update(switcher,t);
        auto final=waitFor(renderer,finalSerial);
        same(final.frame->at(0,0),{0,1,0,1},"Latest replaced program state was not rendered");
        expect(final.serial==finalSerial,"Program renderer published an out-of-date result");

        std::cout<<"PASS: program composition worker, caller-thread capture, fade/interruption continuity, bounded latest-state replacement and shutdown\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<e.what()<<'\n';
        return 1;
    }
}
