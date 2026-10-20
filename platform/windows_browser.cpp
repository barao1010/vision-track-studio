#define NOMINMAX
#include "windows_browser.hpp"
#include <WebView2.h>
#include <wrl.h>
#include <wincodec.h>
#include <shlobj.h>
#include <filesystem>
#include <cmath>
#include <chrono>
#include <stdexcept>
namespace vision {
using Microsoft::WRL::ComPtr;
using Microsoft::WRL::Callback;
namespace {
void check(HRESULT hr) {if(FAILED(hr)) throw std::runtime_error("Browser operation failed (HRESULT "+std::to_string(static_cast<unsigned long>(hr))+")");}
std::wstring javascriptString(const std::wstring& text) {
    const wchar_t hex[]=L"0123456789abcdef";std::wstring out=L"\"";
    for(auto c:text) {auto n=static_cast<unsigned short>(c);out+=L"\\u";for(int shift=12;shift>=0;shift-=4) out+=hex[(n>>shift)&15];}
    return out+L"\"";
}
void validUrl(const std::wstring& url) {
    if(url.empty() || url.size()>32768 || url.find(L'\0')!=std::wstring::npos ||
       !(url.starts_with(L"https://") || url.starts_with(L"http://") || url==L"about:blank"))
        throw std::invalid_argument("Browser URL must use HTTP or HTTPS and fit within 32768 characters");
}
float linear(BYTE v) {float s=v/255.f;return s<=.04045f?s/12.92f:std::pow((s+.055f)/1.055f,2.4f);}
Frame decode(IStream* stream,int width,int height) {
    LARGE_INTEGER zero{};check(stream->Seek(zero,STREAM_SEEK_SET,nullptr));
    ComPtr<IWICImagingFactory> factory;check(CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&factory)));
    ComPtr<IWICBitmapDecoder> decoder;check(factory->CreateDecoderFromStream(stream,nullptr,WICDecodeMetadataCacheOnLoad,&decoder));
    ComPtr<IWICBitmapFrameDecode> bitmap;check(decoder->GetFrame(0,&bitmap));
    UINT w=0,h=0;check(bitmap->GetSize(&w,&h));
    if(w!=static_cast<UINT>(width) || h!=static_cast<UINT>(height)) throw std::runtime_error("Browser capture size changed");
    ComPtr<IWICFormatConverter> converter;check(factory->CreateFormatConverter(&converter));
    check(converter->Initialize(bitmap.Get(),GUID_WICPixelFormat32bppRGBA,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom));
    std::vector<BYTE> bytes(static_cast<std::size_t>(w)*h*4);
    check(converter->CopyPixels(nullptr,w*4,static_cast<UINT>(bytes.size()),bytes.data()));
    Frame frame(width,height);
    for(int y=0;y<height;++y) for(int x=0;x<width;++x) {auto i=(static_cast<std::size_t>(y)*width+x)*4;frame.at(x,y)={linear(bytes[i]),linear(bytes[i+1]),linear(bytes[i+2]),bytes[i+3]/255.f};}
    return frame;
}
}
struct BrowserSource::State {
    HWND host=nullptr;
    int width=0,height=0;
    bool ready=false,pending=false,closed=false;
    std::uint64_t generation=0;
    std::wstring url,css,html;
    ComPtr<ICoreWebView2Controller> controller;
    ComPtr<ICoreWebView2> web;
    std::shared_ptr<const Frame> latest;
    std::exception_ptr error;
    std::chrono::steady_clock::time_point started=std::chrono::steady_clock::now(),lastCapture=started;
    void fail() {error=std::current_exception();pending=false;}
    void close() {
        closed=true;
        if(controller) controller->Close();
        web.Reset();controller.Reset();
        if(host) {DestroyWindow(host);host=nullptr;}
    }
    ~State() {close();}
};
BrowserSource::BrowserSource(std::wstring url,std::wstring css,int width,int height,std::wstring html):state_(std::make_shared<State>()) {
    if(width<1 || height<1 || width>1920 || height>1080 || css.size()>65536 || html.size()>1024*1024) throw std::invalid_argument("Invalid browser source dimensions/content");
    if(html.empty()) validUrl(url);
    auto s=state_;s->width=width;s->height=height;s->url=std::move(url);s->css=std::move(css);s->html=std::move(html);
    s->host=CreateWindowExW(WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE,L"STATIC",L"Vision browser source",WS_POPUP|WS_VISIBLE,-10000,-10000,width,height,nullptr,nullptr,GetModuleHandle(nullptr),nullptr);
    if(!s->host) throw std::runtime_error("Browser host creation failed");
    PWSTR folder=nullptr;check(SHGetKnownFolderPath(FOLDERID_LocalAppData,0,nullptr,&folder));
    std::filesystem::path profile=std::filesystem::path(folder)/L"VisionTrackStudio"/L"Browser";CoTaskMemFree(folder);
    std::filesystem::create_directories(profile);
    std::weak_ptr<State> weak=s;
    check(CreateCoreWebView2EnvironmentWithOptions(nullptr,profile.c_str(),nullptr,
        Callback<ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler>(
        [weak](HRESULT hr,ICoreWebView2Environment* environment)->HRESULT {
            auto s=weak.lock();if(!s || s->closed) return S_OK;
            try {
                check(hr);if(!environment) throw std::runtime_error("WebView2 runtime unavailable");
                check(environment->CreateCoreWebView2Controller(s->host,
                    Callback<ICoreWebView2CreateCoreWebView2ControllerCompletedHandler>(
                    [weak](HRESULT result,ICoreWebView2Controller* controller)->HRESULT {
                        auto s=weak.lock();if(!s || s->closed) {if(controller) controller->Close();return S_OK;}
                        try {
                            check(result);if(!controller) throw std::runtime_error("Browser controller unavailable");
                            s->controller=controller;check(controller->get_CoreWebView2(&s->web));
                            RECT bounds{0,0,s->width,s->height};check(controller->put_Bounds(bounds));check(controller->put_IsVisible(TRUE));
                            ComPtr<ICoreWebView2Controller2> color;check(controller->QueryInterface(IID_PPV_ARGS(&color)));
                            check(color->put_DefaultBackgroundColor({0,0,0,0}));
                            ComPtr<ICoreWebView2Controller3> scale;check(controller->QueryInterface(IID_PPV_ARGS(&scale)));
                            check(scale->put_ShouldDetectMonitorScaleChanges(FALSE));check(scale->put_RasterizationScale(1.0));
                            ComPtr<ICoreWebView2Settings> settings;check(s->web->get_Settings(&settings));
                            check(settings->put_AreDefaultScriptDialogsEnabled(FALSE));
                            ComPtr<ICoreWebView2_8> audio;check(s->web.As(&audio));check(audio->put_IsMuted(TRUE));
                            EventRegistrationToken token{};
                            check(s->web->add_PermissionRequested(Callback<ICoreWebView2PermissionRequestedEventHandler>(
                                [](ICoreWebView2*,ICoreWebView2PermissionRequestedEventArgs* args)->HRESULT {return args->put_State(COREWEBVIEW2_PERMISSION_STATE_DENY);}).Get(),&token));
                            check(s->web->add_NewWindowRequested(Callback<ICoreWebView2NewWindowRequestedEventHandler>(
                                [](ICoreWebView2*,ICoreWebView2NewWindowRequestedEventArgs* args)->HRESULT {return args->put_Handled(TRUE);}).Get(),&token));
                            check(s->web->add_NavigationStarting(Callback<ICoreWebView2NavigationStartingEventHandler>(
                                [weak](ICoreWebView2*,ICoreWebView2NavigationStartingEventArgs*)->HRESULT {
                                    auto s=weak.lock();if(s && !s->closed) {s->ready=false;++s->generation;s->latest.reset();s->started=std::chrono::steady_clock::now();}
                                    return S_OK;
                                }).Get(),&token));
                            check(s->web->add_NavigationCompleted(Callback<ICoreWebView2NavigationCompletedEventHandler>(
                                [weak](ICoreWebView2*,ICoreWebView2NavigationCompletedEventArgs* args)->HRESULT {
                                    auto s=weak.lock();if(!s || s->closed) return S_OK;
                                    try {
                                        BOOL success=FALSE;check(args->get_IsSuccess(&success));if(!success) throw std::runtime_error("Browser navigation failed");
                                        apply_css(s);
                                    } catch(...) {s->fail();}
                                    return S_OK;
                                }).Get(),&token));
                            if(s->html.empty()) check(s->web->Navigate(s->url.c_str()));else check(s->web->NavigateToString(s->html.c_str()));
                        } catch(...) {s->fail();}
                        return S_OK;
                    }).Get()));
            } catch(...) {s->fail();}
            return S_OK;
        }).Get()));
}
void BrowserSource::apply_css(const std::shared_ptr<State>& s) {
    s->ready=false;s->latest.reset();auto generation=++s->generation;
    std::weak_ptr<State> weak=s;
    auto script=L"(()=>{let s=document.getElementById('__vision_custom_css');if(!s){s=document.createElement('style');s.id='__vision_custom_css';document.documentElement.appendChild(s);}s.textContent="+javascriptString(s->css)+L";})()";
    check(s->web->ExecuteScript(script.c_str(),Callback<ICoreWebView2ExecuteScriptCompletedHandler>(
        [weak,generation](HRESULT result,LPCWSTR)->HRESULT {
            auto s=weak.lock();if(!s || s->closed || generation!=s->generation) return S_OK;
            try {check(result);s->ready=true;}catch(...){s->fail();}return S_OK;
        }).Get()));
}
void BrowserSource::set_css(std::wstring css) const {
    if(css.size()>65536) throw std::invalid_argument("Browser CSS is too large");
    auto s=state_;if(s->error) std::rethrow_exception(s->error);
    if(!s->ready) throw std::runtime_error("Wait for the browser to finish loading before editing CSS");
    s->css=std::move(css);s->started=std::chrono::steady_clock::now();apply_css(s);
}
void BrowserSource::navigate(std::wstring url) const {
    validUrl(url);auto s=state_;
    if(!s->web) throw std::runtime_error("Browser is still initializing");
    if(!s->ready && !s->error) throw std::runtime_error("Browser is already loading");
    s->ready=false;s->latest.reset();s->error=nullptr;++s->generation;
    s->started=std::chrono::steady_clock::now();
    try {check(s->web->Navigate(url.c_str()));}
    catch(...) {s->fail();throw;}
    s->url=std::move(url);s->html.clear();
}
void BrowserSource::reload() const {
    auto s=state_;if(!s->web) throw std::runtime_error("Browser is still initializing");
    if(!s->ready && !s->error) throw std::runtime_error("Browser is already loading");
    // Invalidate captures before navigation starts; never publish the old page after reload.
    s->ready=false;s->latest.reset();s->error=nullptr;++s->generation;
    s->started=std::chrono::steady_clock::now();
    if(s->html.empty()) check(s->web->Navigate(s->url.c_str()));else check(s->web->NavigateToString(s->html.c_str()));
}
BrowserSource::~BrowserSource() {state_->close();}
Frame BrowserSource::frame(std::int64_t) const {
    auto s=state_;if(s->error) std::rethrow_exception(s->error);
    auto now=std::chrono::steady_clock::now();
    if(!s->ready && now-s->started>std::chrono::seconds(30)) throw std::runtime_error("Browser initialization timed out");
    if(s->pending && now-s->lastCapture>std::chrono::seconds(10)) throw std::runtime_error("Browser capture timed out");
    if(s->ready && !s->pending && now-s->lastCapture>=std::chrono::milliseconds(100)) {
        ComPtr<IStream> stream;check(CreateStreamOnHGlobal(nullptr,TRUE,&stream));
        s->pending=true;s->lastCapture=now;std::weak_ptr<State> weak=s;
        auto generation=s->generation;
        auto hr=s->web->CapturePreview(COREWEBVIEW2_CAPTURE_PREVIEW_IMAGE_FORMAT_PNG,stream.Get(),
            Callback<ICoreWebView2CapturePreviewCompletedHandler>([weak,stream,generation](HRESULT result)->HRESULT {
                auto s=weak.lock();if(!s || s->closed) return S_OK;
                if(generation!=s->generation) {s->pending=false;return S_OK;}
                try {check(result);s->latest=std::make_shared<Frame>(decode(stream.Get(),s->width,s->height));s->pending=false;}catch(...){s->fail();}
                return S_OK;
            }).Get());
        if(FAILED(hr)) {s->pending=false;check(hr);}
    }
    return s->latest?*s->latest:Frame(s->width,s->height);
}
}
