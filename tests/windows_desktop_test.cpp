#define NOMINMAX
#include <windows.h>
#include "windows_desktop.hpp"
#include <iostream>
LRESULT CALLBACK colorWindow(HWND w,UINT m,WPARAM a,LPARAM b) {
    if(m==WM_PAINT) {PAINTSTRUCT p{};HDC dc=BeginPaint(w,&p);RECT r;GetClientRect(w,&r);HBRUSH brush=CreateSolidBrush(RGB(255,0,0));FillRect(dc,&r,brush);DeleteObject(brush);EndPaint(w,&p);return 0;}
    return DefWindowProc(w,m,a,b);
}
int main() {
    WNDCLASSW cls{};cls.lpfnWndProc=colorWindow;cls.hInstance=GetModuleHandle(nullptr);cls.lpszClassName=L"VisionCaptureTest";RegisterClassW(&cls);
    HWND window=CreateWindowExW(WS_EX_TOPMOST,cls.lpszClassName,L"Capture validation",WS_POPUP|WS_VISIBLE,GetSystemMetrics(SM_XVIRTUALSCREEN),GetSystemMetrics(SM_YVIRTUALSCREEN),GetSystemMetrics(SM_CXVIRTUALSCREEN),GetSystemMetrics(SM_CYVIRTUALSCREEN),nullptr,nullptr,cls.hInstance,nullptr);
    if(!window) return 1;
    UpdateWindow(window);GdiFlush();int result=0;
    try {
        vision::DesktopSource source;
        for(int i=0;i<5;++i) {auto frame=source.frame(i);auto p=frame.at(320,180);if(p.r<.9f || p.g>.05f || p.b>.05f) throw std::runtime_error("Captured pixel does not match desktop window");}
        std::cout<<"PASS: desktop pixels captured through Windows GDI\n";
    }catch(const std::exception& e) {std::cerr<<e.what()<<'\n';result=1;}
    DestroyWindow(window);return result;
}
