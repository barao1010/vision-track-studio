#include "media.hpp"
#include <cmath>
#include <iostream>
#include <numbers>
using namespace vision;
int main(int argc,char** argv) {
    try {
        if(argc!=4) throw std::invalid_argument("render_fixture COLOR.ppm IMAGE.ppm OUTPUT_DIRECTORY");
        auto scene=[](const char* path) {auto s=std::make_shared<Scene>();s->add({"fixture",std::make_shared<StillSource>(read_ppm(path)),0,0,640,360,{}});return s;};
        auto color=scene(argv[1]),image=scene(argv[2]);
        Switcher sw(640,360,color);RawRecorder recorder(argv[3],640,360,30,48000);
        for(int frame=0;frame<210;++frame) {
            const std::int64_t ns=static_cast<std::int64_t>(frame)*1000000000/30;
            if(frame==105) sw.take(image,ns,300000000);
            AudioBlock tone{static_cast<std::int64_t>(frame)*1600,2,{}};
            tone.samples.reserve(3200);
            for(int j=0;j<1600;++j) {
                const double phase=2*std::numbers::pi*440*static_cast<double>(tone.start_sample+j)/48000;
                const auto pcm=static_cast<int>(8000*std::sin(phase));
                float sample=static_cast<float>(pcm)/32768.f;
                tone.samples.push_back(sample);tone.samples.push_back(sample);
            }
            auto audio=mix(tone.start_sample,1600,2,{{&tone,.8f,false}});
            recorder.append(sw.render(ns),audio.block);
        }
        recorder.finish();std::cout<<"Rendered 210 video frames and 336000 stereo samples\n";
    }catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
