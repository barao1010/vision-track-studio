#define NOMINMAX
#include "windows_camera.hpp"
#include <mfapi.h>
#include <wrl/client.h>
#include <iostream>
#include <stdexcept>
#include <cstring>
using Microsoft::WRL::ComPtr;
void check(bool ok) {if(!ok) throw std::runtime_error("Camera buffer contract failed");}
int main() {
    if(FAILED(CoInitializeEx(nullptr,COINIT_MULTITHREADED))) return 1;
    if(FAILED(MFStartup(MF_VERSION))) {CoUninitialize();return 1;}
    int result=0;
    try {
        ComPtr<IMFMediaBuffer> buffer;check(SUCCEEDED(MFCreateMemoryBuffer(24,&buffer)));
        BYTE* bytes=nullptr;check(SUCCEEDED(buffer->Lock(&bytes,nullptr,nullptr)));
        // Two 2px rows with 4 padding bytes: red/green then blue/white.
        BYTE pixels[24]={0,0,255,0,0,255,0,0,99,99,99,99,255,0,0,0,255,255,255,0,88,88,88,88};
        std::memcpy(bytes,pixels,24);buffer->Unlock();check(SUCCEEDED(buffer->SetCurrentLength(24)));
        auto top=vision::camera_rgb32(buffer.Get(),2,2,12);
        check(top.at(0,0).r==1 && top.at(1,0).g==1 && top.at(0,1).b==1 && top.at(1,1).a==1);
        auto bottom=vision::camera_rgb32(buffer.Get(),2,2,-12);check(bottom.at(0,0).b==1 && bottom.at(0,1).r==1);
        bool rejected=false;try {vision::camera_rgb32(buffer.Get(),2,2,16);}catch(const std::exception&) {rejected=true;}check(rejected);
        // A failed conversion must still unlock the buffer.
        check(SUCCEEDED(buffer->Lock(&bytes,nullptr,nullptr)));buffer->Unlock();
        ComPtr<IMFMediaBuffer> image;check(SUCCEEDED(MFCreate2DMediaBuffer(2,2,MFVideoFormat_RGB32.Data1,TRUE,&image)));
        ComPtr<IMF2DBuffer> two;check(SUCCEEDED(image.As(&two)));LONG pitch=0;
        check(SUCCEEDED(two->Lock2D(&bytes,&pitch)));
        for(int y=0;y<2;++y) for(int x=0;x<2;++x) {
            auto pixel=bytes+static_cast<std::ptrdiff_t>(y)*pitch+4*x;
            pixel[0]=y?255:0;pixel[1]=0;pixel[2]=y?0:255;pixel[3]=0;
        }
        check(SUCCEEDED(two->Unlock2D()));
        auto imageFrame=vision::camera_rgb32(image.Get(),2,2,8);
        check(imageFrame.at(0,0).r==1 && imageFrame.at(0,1).b==1);
        auto devices=vision::camera_devices();
        for(const auto& d:devices) check(!d.id.empty());
        std::cout<<"PASS: RGB32 padded rows, negative stride, opaque alpha, truncated buffers, enumeration; no physical camera opened\n";
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';result=1;}
    MFShutdown();CoUninitialize();return result;
}
