#define NOMINMAX
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <commdlg.h>
#include <wincodec.h>
#include <wrl/client.h>
#include "core.hpp"
#include "windows_desktop.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <stdexcept>
using namespace vision;
using Microsoft::WRL::ComPtr;
namespace {
constexpr int SceneList=101, AddScene=102, AddImage=103, SourceList=104, Toggle=105, Remove=106, Cut=107, Fade=108, Smaller=109, Larger=110, AddDesktop=111;
HWND window=nullptr,scenesBox=nullptr,sourcesBox=nullptr;
std::vector<std::shared_ptr<Scene>> scenes;
std::vector<std::vector<std::string>> ids;
std::unique_ptr<Switcher> program;
int selected=0,serial=0;
bool smoke=false;
int smokeStep=0;
std::int64_t now() {return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
void hr(HRESULT r) {if(FAILED(r)) throw std::runtime_error("Windows image decoder failed");}
float linear(BYTE b) {float s=b/255.f;return s<=.04045f?s/12.92f:std::pow((s+.055f)/1.055f,2.4f);}
BYTE encoded(float l) {l=std::clamp(l,0.f,1.f);return static_cast<BYTE>(std::lround(255*(l<=.0031308f?12.92f*l:1.055f*std::pow(l,1.f/2.4f)-.055f)));}
Frame imageFile(const wchar_t* name) {
    ComPtr<IWICImagingFactory> factory;hr(CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&factory)));
    ComPtr<IWICBitmapDecoder> decoder;hr(factory->CreateDecoderFromFilename(name,nullptr,GENERIC_READ,WICDecodeMetadataCacheOnLoad,&decoder));
    ComPtr<IWICBitmapFrameDecode> bitmap;hr(decoder->GetFrame(0,&bitmap));
    UINT w=0,h=0;hr(bitmap->GetSize(&w,&h));
    if(w==0 || h==0 || w>8192 || h>8192) throw std::runtime_error("Image dimensions out of range");
    ComPtr<IWICFormatConverter> converter;hr(factory->CreateFormatConverter(&converter));
    hr(converter->Initialize(bitmap.Get(),GUID_WICPixelFormat32bppRGBA,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom));
    std::vector<BYTE> bytes(static_cast<std::size_t>(w)*h*4);
    hr(converter->CopyPixels(nullptr,w*4,static_cast<UINT>(bytes.size()),bytes.data()));
    Frame output(static_cast<int>(w),static_cast<int>(h));
    for(UINT y=0;y<h;++y) for(UINT x=0;x<w;++x) {auto offset=(static_cast<std::size_t>(y)*w+x)*4;output.at(static_cast<int>(x),static_cast<int>(y))={linear(bytes[offset]),linear(bytes[offset+1]),linear(bytes[offset+2]),bytes[offset+3]/255.f};}
    return output;
}
void refresh() {
    SendMessage(sourcesBox,LB_RESETCONTENT,0,0);
    for(const auto& id:ids.at(selected)) {std::wstring label(id.begin(),id.end());if(!scenes[selected]->item(id).visible) label+=L" (oculta)";SendMessage(sourcesBox,LB_ADDSTRING,0,reinterpret_cast<LPARAM>(label.c_str()));}
    if(!ids[selected].empty()) SendMessage(sourcesBox,LB_SETCURSEL,ids[selected].size()-1,0);
    InvalidateRect(window,nullptr,FALSE);
}
void addSource(Frame image) {
    auto id="Imagem "+std::to_string(++serial);
    double scale=std::min(640.0/image.width(),360.0/image.height());
    int w=std::max(1,static_cast<int>(image.width()*scale)),h=std::max(1,static_cast<int>(image.height()*scale));
    scenes[selected]->add({id,std::make_shared<StillSource>(std::move(image)),(640-w)/2,(360-h)/2,w,h,{}});
    ids[selected].push_back(id);refresh();
}
void addScene() {
    scenes.push_back(std::make_shared<Scene>());ids.emplace_back();selected=static_cast<int>(scenes.size())-1;
    auto name=L"Cena "+std::to_wstring(scenes.size());SendMessage(scenesBox,LB_ADDSTRING,0,reinterpret_cast<LPARAM>(name.c_str()));SendMessage(scenesBox,LB_SETCURSEL,selected,0);refresh();
}
Item* selectedItem() {auto index=SendMessage(sourcesBox,LB_GETCURSEL,0,0);if(index==LB_ERR) return nullptr;return &scenes[selected]->item(ids[selected].at(static_cast<std::size_t>(index)));}
void command(int id) {
    if(id==AddScene) addScene();
    else if(id==AddDesktop) {
        auto key="Tela "+std::to_string(++serial);
        scenes[selected]->add({key,std::make_shared<DesktopSource>(),0,0,640,360,{}});
        ids[selected].push_back(key);refresh();
    }
    else if(id==AddImage) {
        wchar_t path[32768]={};OPENFILENAME ofn{};ofn.lStructSize=sizeof(ofn);ofn.hwndOwner=window;ofn.lpstrFile=path;ofn.nMaxFile=32768;ofn.lpstrFilter=L"Imagens\0*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff\0Todos\0*.*\0";ofn.Flags=OFN_FILEMUSTEXIST|OFN_PATHMUSTEXIST|OFN_NOCHANGEDIR;
        if(GetOpenFileName(&ofn)) addSource(imageFile(path));
    } else if(id==Cut || id==Fade) program->take(scenes[selected],now(),id==Cut?0:300000000);
    else if(auto* item=selectedItem()) {
        if(id==Toggle) item->visible=!item->visible;
        if(id==Smaller || id==Larger) {double factor=id==Smaller?.9:1.1;item->width=std::clamp(static_cast<int>(item->width*factor),1,8192);item->height=std::clamp(static_cast<int>(item->height*factor),1,8192);item->x=(640-item->width)/2;item->y=(360-item->height)/2;}
        if(id==Remove) {auto key=item->id;scenes[selected]->remove(key);std::erase(ids[selected],key);}
        refresh();
    }
}
void draw(HDC dc,const Frame& f,int x,int y,int w,int h) {
    std::vector<BYTE> data(static_cast<std::size_t>(f.width())*f.height()*4);
    for(int row=0;row<f.height();++row) for(int col=0;col<f.width();++col) {auto p=f.at(col,row);auto n=(static_cast<std::size_t>(row)*f.width()+col)*4;data[n]=encoded(p.b*p.a);data[n+1]=encoded(p.g*p.a);data[n+2]=encoded(p.r*p.a);}
    BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=f.width();info.bmiHeader.biHeight=-f.height();info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
    StretchDIBits(dc,x,y,w,h,0,0,f.width(),f.height(),data.data(),&info,DIB_RGB_COLORS,SRCCOPY);
}
HWND control(const wchar_t* cls,const wchar_t* text,int id,int x,int y,int w,int h,DWORD extra=0) {
    HWND result=CreateWindow(cls,text,WS_CHILD|WS_VISIBLE|extra,x,y,w,h,window,reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)),GetModuleHandle(nullptr),nullptr);
    if(!result) throw std::runtime_error("Could not create control");SendMessage(result,WM_SETFONT,reinterpret_cast<WPARAM>(GetStockObject(DEFAULT_GUI_FONT)),TRUE);return result;
}
void verify(bool ok) {if(!ok) throw std::runtime_error("GUI action contract failed");}
LRESULT CALLBACK proc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp) {
    try {
        switch(msg) {
        case WM_CREATE:
            window=hwnd;
            control(L"STATIC",L"Cenas",0,15,15,180,25);
            scenesBox=control(L"LISTBOX",L"",SceneList,15,40,180,150,LBS_NOTIFY|WS_BORDER|WS_VSCROLL);
            control(L"BUTTON",L"Adicionar cena",AddScene,15,195,180,30);
            control(L"STATIC",L"Fontes da previa",0,15,235,180,25);
            sourcesBox=control(L"LISTBOX",L"",SourceList,15,260,180,120,WS_BORDER|WS_VSCROLL);
            control(L"BUTTON",L"Adicionar imagem",AddImage,15,385,180,30);
            control(L"BUTTON",L"Mostrar / ocultar",Toggle,15,420,180,30);
            control(L"BUTTON",L"Remover fonte",Remove,15,455,180,30);
            control(L"BUTTON",L"Diminuir",Smaller,15,490,85,30);control(L"BUTTON",L"Ampliar",Larger,105,490,90,30);
            control(L"BUTTON",L"Capturar tela",AddDesktop,15,525,180,30);
            control(L"STATIC",L"PREVIA",0,220,15,300,25);control(L"STATIC",L"PROGRAMA",0,560,15,300,25);
            control(L"BUTTON",L"Corte",Cut,220,240,150,35);control(L"BUTTON",L"Fade 300 ms",Fade,380,240,150,35);
            control(L"STATIC",L"Desenvolvimento: cenas, imagens e tela. Camera, microfone e transmissao pendentes.",0,220,300,660,50);
            addScene();program=std::make_unique<Switcher>(640,360,scenes[0]);SetTimer(hwnd,1,33,nullptr);return 0;
        case WM_COMMAND:
            if(LOWORD(wp)==SceneList && HIWORD(wp)==LBN_SELCHANGE) {auto s=SendMessage(scenesBox,LB_GETCURSEL,0,0);if(s!=LB_ERR) {selected=static_cast<int>(s);refresh();}}
            else if(HIWORD(wp)==BN_CLICKED) command(LOWORD(wp));return 0;
        case WM_TIMER:
            if(smoke) {
                if(smokeStep==0) {addSource(Frame(2,2,{1,0,0,1}));SendMessage(hwnd,WM_COMMAND,Cut,0);verify(program->render(now()).at(320,180).r==1);SendMessage(hwnd,WM_COMMAND,AddScene,0);addSource(Frame(2,2,{0,0,1,1}));SendMessage(hwnd,WM_COMMAND,Fade,0);}
                if(smokeStep==20) {verify(program->render(now()).at(320,180).b==1);SendMessage(hwnd,WM_COMMAND,Toggle,0);verify(program->render(now()).at(320,180).a==0);SendMessage(hwnd,WM_COMMAND,Toggle,0);SendMessage(hwnd,WM_COMMAND,Remove,0);verify(ids[selected].empty());std::ofstream("gui-smoke.txt")<<"PASS: window, scene creation, cut, fade, visibility, source removal\n";DestroyWindow(hwnd);return 0;}
                ++smokeStep;
            }
            InvalidateRect(hwnd,nullptr,FALSE);return 0;
        case WM_PAINT: {PAINTSTRUCT ps{};auto dc=BeginPaint(hwnd,&ps);try {if(program) {draw(dc,scenes[selected]->render(640,360,now()),220,45,320,180);draw(dc,program->render(now()),560,45,320,180);}}catch(...) {EndPaint(hwnd,&ps);KillTimer(hwnd,1);throw;}EndPaint(hwnd,&ps);return 0;}
        case WM_DESTROY: KillTimer(hwnd,1);program.reset();scenes.clear();PostQuitMessage(0);return 0;
        }
    }catch(const std::exception& e) {
        if(smoke) {std::ofstream("gui-smoke.txt")<<"FAIL: "<<e.what();PostQuitMessage(1);}
        else MessageBoxA(hwnd,e.what(),"Vision Track Studio",MB_OK|MB_ICONERROR);
        if(msg==WM_CREATE) return -1;
    }
    return DefWindowProc(hwnd,msg,wp,lp);
}
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE,PWSTR cmd,int show) {
    smoke=std::wstring(cmd).find(L"--self-test-gui")!=std::wstring::npos;
    if(FAILED(CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED))) return 1;
    WNDCLASS cls{};cls.lpfnWndProc=proc;cls.hInstance=instance;cls.lpszClassName=L"VisionIndependentStudio";cls.hbrBackground=reinterpret_cast<HBRUSH>(COLOR_WINDOW+1);cls.hCursor=LoadCursor(nullptr,IDC_ARROW);
    if(!RegisterClass(&cls)) {CoUninitialize();return 1;}
    HWND main=CreateWindow(cls.lpszClassName,L"Vision Track Studio - desenvolvimento independente",WS_OVERLAPPEDWINDOW,CW_USEDEFAULT,CW_USEDEFAULT,930,590,nullptr,nullptr,instance,nullptr);
    if(!main) {CoUninitialize();return 1;}ShowWindow(main,show);
    MSG message{};int status;
    while((status=GetMessage(&message,nullptr,0,0))>0) {TranslateMessage(&message);DispatchMessage(&message);}
    CoUninitialize();return status<0?1:static_cast<int>(message.wParam);
}
