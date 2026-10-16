#define NOMINMAX
#include "windows_desktop.hpp"
#include <windows.h>
#include <cmath>
#include <stdexcept>
namespace vision {
namespace {
struct CaptureHandles {
    HDC desktop=GetDC(nullptr), memory=nullptr;
    HBITMAP bitmap=nullptr;
    HGDIOBJ previous=nullptr;
    ~CaptureHandles() {
        if(previous && memory) SelectObject(memory,previous);
        if(bitmap) DeleteObject(bitmap);
        if(memory) DeleteDC(memory);
        if(desktop) ReleaseDC(nullptr,desktop);
    }
};
float linear(BYTE v) {float s=v/255.f;return s<=.04045f?s/12.92f:std::pow((s+.055f)/1.055f,2.4f);}
}
Frame DesktopSource::frame(std::int64_t) const {
    if(width_<=0 || height_<=0 || width_>3840 || height_>2160) throw std::invalid_argument("Invalid desktop capture size");
    CaptureHandles handles;
    if(!handles.desktop) throw std::runtime_error("Desktop unavailable");
    handles.memory=CreateCompatibleDC(handles.desktop);
    if(!handles.memory) throw std::runtime_error("Capture context unavailable");
    BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=width_;info.bmiHeader.biHeight=-height_;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
    void* raw=nullptr;
    handles.bitmap=CreateDIBSection(handles.desktop,&info,DIB_RGB_COLORS,&raw,nullptr,0);
    if(!handles.bitmap || !raw) throw std::runtime_error("Capture buffer unavailable");
    handles.previous=SelectObject(handles.memory,handles.bitmap);
    if(!handles.previous || handles.previous==HGDI_ERROR) {handles.previous=nullptr;throw std::runtime_error("Cannot select capture buffer");}
    int x=GetSystemMetrics(SM_XVIRTUALSCREEN),y=GetSystemMetrics(SM_YVIRTUALSCREEN),w=GetSystemMetrics(SM_CXVIRTUALSCREEN),h=GetSystemMetrics(SM_CYVIRTUALSCREEN);
    if(w<=0 || h<=0) throw std::runtime_error("No desktop display available");
    SetStretchBltMode(handles.memory,HALFTONE);SetBrushOrgEx(handles.memory,0,0,nullptr);
    if(!StretchBlt(handles.memory,0,0,width_,height_,handles.desktop,x,y,w,h,SRCCOPY|CAPTUREBLT)) throw std::runtime_error("Desktop capture failed");
    GdiFlush();
    Frame out(width_,height_);const auto* pixels=static_cast<const BYTE*>(raw);
    for(int row=0;row<height_;++row) for(int col=0;col<width_;++col) {auto n=(static_cast<std::size_t>(row)*width_+col)*4;out.at(col,row)={linear(pixels[n+2]),linear(pixels[n+1]),linear(pixels[n]),1};}
    return out;
}
}
