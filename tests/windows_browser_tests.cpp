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
        auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(25);bool passed=false;
        while(std::chrono::steady_clock::now()<deadline) {
            MSG msg;while(PeekMessage(&msg,nullptr,0,0,PM_REMOVE)) {TranslateMessage(&msg);DispatchMessage(&msg);}
            auto f=source.frame(0);auto red=f.at(30,30),empty=f.at(120,100);
            if(red.r>.95f && red.b<.01f && red.a>.99f && empty.a<.01f) {passed=true;break;}
            MsgWaitForMultipleObjects(0,nullptr,FALSE,20,QS_ALLINPUT);
        }
        if(!passed) throw std::runtime_error("Browser CSS/red pixels/transparent background did not render");
        std::cout<<"PASS: actual WebView2 HTML, CSS override and transparent pixels captured into compositor frame\n";
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';result=1;}
    CoUninitialize();return result;
}
