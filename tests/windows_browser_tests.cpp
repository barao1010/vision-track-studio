#define NOMINMAX
#include "windows_browser.hpp"
#include <chrono>
#include <iostream>
#include <stdexcept>
int main() {
    if(FAILED(CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED))) return 1;
    int result=0;
    try {
        vision::BrowserSource source(L"about:blank",
            L"html,body{margin:0;background:transparent!important} #box{width:80px;height:80px;background:rgb(255,0,0)!important}",
            160,120,L"<html><body><div id='box' style='background:blue'></div></body></html>");
        auto wait=[&](bool green) {
            auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(25);
            while(std::chrono::steady_clock::now()<deadline) {
                MSG msg;while(PeekMessage(&msg,nullptr,0,0,PM_REMOVE)) {TranslateMessage(&msg);DispatchMessage(&msg);}
                auto f=source.frame(0);auto pixel=f.at(30,30),empty=f.at(120,100);
                if(pixel.a>.99f && empty.a<.01f && pixel.b<.01f &&
                   (green?(pixel.g>.95f && pixel.r<.01f):(pixel.r>.95f && pixel.g<.01f))) return;
                MsgWaitForMultipleObjects(0,nullptr,FALSE,20,QS_ALLINPUT);
            }
            throw std::runtime_error("Browser CSS/red or green pixels/transparent background did not render");
        };
        wait(false);
        bool rejected=false;
        try {source.set_css(std::wstring(65537,L'x'));} catch(const std::invalid_argument&) {rejected=true;}
        if(!rejected) throw std::runtime_error("Oversized CSS accepted");
        source.set_css(L"html,body{margin:0;background:transparent!important} #box{width:80px;height:80px;background:rgb(0,255,0)!important}");
        if(source.frame(0).at(30,30).a!=0) throw std::runtime_error("Stale frame published after CSS edit");
        wait(true);
        source.reload();
        if(source.frame(0).at(30,30).a!=0) throw std::runtime_error("Stale frame published after reload");
        wait(true);
        std::cout<<"PASS: actual WebView2 HTML, CSS override replacement, reload and transparent pixels captured into compositor frame\n";
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';result=1;}
    CoUninitialize();return result;
}
