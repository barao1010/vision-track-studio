#include <windows.h>
#include <mfapi.h>
#include "windows_recording.hpp"
#include <cmath>
#include <iostream>
#include <numbers>
int main(int argc,char** argv) {
    if(argc!=2) return 1;
    if(FAILED(CoInitializeEx(nullptr,COINIT_MULTITHREADED))) return 1;
    if(FAILED(MFStartup(MF_VERSION))) {CoUninitialize();return 1;}
    int result=0;
    try {
        vision::WindowsRecorder recorder(argv[1],640,360,30);
        for(int n=0;n<90;++n) {
            vision::Frame frame(640,360,{0,0,1,1});
            for(int y=0;y<180;++y) for(int x=0;x<640;++x) frame.at(x,y)={1,0,0,1};
            vision::AudioBlock block{static_cast<std::int64_t>(n)*1600,2,{}};
            for(int j=0;j<1600;++j) {float value=static_cast<float>(.2*std::sin(2*std::numbers::pi*440*static_cast<double>(block.start_sample+j)/48000));block.samples.push_back(value);block.samples.push_back(value);}
            recorder.append(frame,block);
        }
        recorder.finish();recorder.finish();
        std::cout<<"Encoded 90 video frames with stereo tone using Windows Media Foundation\n";
    }catch(const std::exception& e) {std::cerr<<e.what()<<'\n';result=1;}
    MFShutdown();CoUninitialize();return result;
}
