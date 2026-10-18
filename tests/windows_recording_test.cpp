#include <windows.h>
#include <mfapi.h>
#include "windows_output.hpp"
#include "recording_rate.hpp"
#include <cmath>
#include <iostream>
#include <numbers>
int main(int argc,char** argv) {
    if(argc<2 || argc>4) return 1;
    if(FAILED(CoInitializeEx(nullptr,COINIT_MULTITHREADED))) return 1;
    if(FAILED(MFStartup(MF_VERSION))) {CoUninitialize();return 1;}
    int result=0;
    try {
        int fps=argc>=3?std::stoi(argv[2]):30;
        int audioFrames=vision::recording_audio_frames(fps);
        int kbps=argc==4?std::stoi(argv[3]):4000;
        auto recorder=vision::create_windows_output(argv[1],false,true,fps,kbps);
        for(int n=0;n<fps*3;++n) {
            vision::Frame frame(640,360,{0,0,1,1});
            for(int y=0;y<180;++y) for(int x=0;x<640;++x) frame.at(x,y)={1,0,0,1};
            recorder->write({std::make_shared<vision::Frame>(std::move(frame)),n,static_cast<std::int64_t>(n)*audioFrames,1,false});
        }
        recorder->finish();recorder->finish();
        std::cout<<"Encoded three seconds of video with stereo tone using Windows Media Foundation\n";
    }catch(const std::exception& e) {std::cerr<<e.what()<<'\n';result=1;}
    MFShutdown();CoUninitialize();return result;
}
