#define NOMINMAX
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <commdlg.h>
#include <commctrl.h>
#include <wincodec.h>
#include <mfapi.h>
#include <wrl/client.h>
#include "core.hpp"
#include "project.hpp"
#include <map>
#include <charconv>
#include <array>
#include "windows_desktop.hpp"
#include "windows_camera.hpp"
#include "windows_output.hpp"
#include "audio_buffer.hpp"
#include "scheduled_output.hpp"
#include <numbers>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <stdexcept>
using namespace vision;
using Microsoft::WRL::ComPtr;
namespace {
constexpr int SceneList=101, AddScene=102, AddImage=103, SourceList=104, Toggle=105, Remove=106, Cut=107, Fade=108, Smaller=109, Larger=110, AddDesktop=111, Record=112, UseMic=113, Mute=114, Gain=115, MeterLabel=116, SaveProject=117, OpenProject=118, LayerUp=119, LayerDown=120, ApplyTransform=121, TransformFirst=130, CameraList=150, RefreshCameras=151, AddCamera=152, ReconnectCamera=153, RecordingRate=154;
HWND window=nullptr,scenesBox=nullptr,sourcesBox=nullptr;
std::vector<std::shared_ptr<Scene>> scenes;
std::vector<std::vector<std::string>> ids;
std::unique_ptr<Switcher> program;
int selected=0,serial=0,programScene=0;
std::vector<std::string> sceneNames;
std::vector<CameraDevice> cameras;
constexpr std::array<int,5> recordingRates{24,25,30,50,60};
int chosenRate() {auto index=SendMessage(GetDlgItem(window,RecordingRate),CB_GETCURSEL,0,0);return recordingRates.at(static_cast<std::size_t>(index));}
std::map<std::shared_ptr<const VideoSource>,SourceDefinition> definitions;
std::string utf8(const std::filesystem::path& path) {
    auto s=path.u8string();return {reinterpret_cast<const char*>(s.data()),s.size()};
}
std::wstring wide(const std::string& text) {
    int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),nullptr,0);
    if(n<=0) throw std::runtime_error("Invalid UTF-8 project name");
    std::wstring out(n,L' ');MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),out.data(),n);return out;
}
std::string nextId(const std::string& prefix) {
    for(;;) {
        auto id=prefix+std::to_string(++serial);bool used=false;
        for(const auto& list:ids) if(std::find(list.begin(),list.end(),id)!=list.end()) used=true;
        for(const auto& entry:definitions) if(entry.second.id==id) used=true;
        if(!used) return id;
    }
}
bool smoke=false, smokeAudio=false;
int smokeStep=0;
std::unique_ptr<ScheduledOutput> recorder;
void recordFrame(std::shared_ptr<const Frame> frame) {
    const bool muted=SendMessage(GetDlgItem(window,Mute),BM_GETCHECK,0,0)==BST_CHECKED;
    const auto db=static_cast<int>(SendMessage(GetDlgItem(window,Gain),TBM_GETPOS,0,0));
    recorder->update(std::move(frame),std::pow(10.f,db/20.f),muted);
    const auto meter=recorder->meter();
    std::wstring level=L"Nivel: ";
    if(meter.peak>0) level+=std::to_wstring(static_cast<int>(std::lround(20*std::log10(meter.peak))))+L" dBFS";
    else level+=L"silencio";
    SetWindowText(GetDlgItem(window,MeterLabel),level.c_str());
}
void startRecording(const std::filesystem::path& path);
void stopRecording() {
    if(!recorder) return;
    auto finishing=std::move(recorder);
    EnableWindow(GetDlgItem(window,UseMic),TRUE);
    EnableWindow(GetDlgItem(window,RecordingRate),TRUE);
    SetWindowText(GetDlgItem(window,Record),L"Gravar MP4");
    finishing->finish();
}

std::int64_t now() {return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
void startRecording(const std::filesystem::path& path) {
    if(recorder) throw std::logic_error("Recording already active");
    const bool useMicrophone=SendMessage(GetDlgItem(window,UseMic),BM_GETCHECK,0,0)==BST_CHECKED;
    const bool testAudio=smokeAudio;
    const auto db=static_cast<int>(SendMessage(GetDlgItem(window,Gain),TBM_GETPOS,0,0));
    const bool muted=SendMessage(GetDlgItem(window,Mute),BM_GETCHECK,0,0)==BST_CHECKED;
    const int fps=chosenRate();
    auto initial=std::make_shared<Frame>(program->render(now()));
    auto starting=std::make_unique<ScheduledOutput>([path,useMicrophone,testAudio,fps]{return create_windows_output(path,useMicrophone,testAudio,fps);},initial,std::pow(10.f,db/20.f),muted,fps);
    EnableWindow(GetDlgItem(window,UseMic),FALSE);
    EnableWindow(GetDlgItem(window,RecordingRate),FALSE);
    recorder=std::move(starting);
    SetWindowText(GetDlgItem(window,Record),useMicrophone?L"Parar gravacao (microfone)":L"Parar gravacao (sem microfone)");
}
void captureRecording(std::int64_t timestamp) {
    if(!recorder) return;
    recordFrame(std::make_shared<Frame>(program->render(timestamp)));
}
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
void loadTransform();
void refresh() {
    SendMessage(sourcesBox,LB_RESETCONTENT,0,0);
    for(const auto& id:ids.at(selected)) {auto label=wide(id);if(!scenes[selected]->item(id).visible) label+=L" (oculta)";SendMessage(sourcesBox,LB_ADDSTRING,0,reinterpret_cast<LPARAM>(label.c_str()));}
    if(!ids[selected].empty()) SendMessage(sourcesBox,LB_SETCURSEL,ids[selected].size()-1,0);
    loadTransform();InvalidateRect(window,nullptr,FALSE);
}
void addSource(Frame image,SourceDefinition definition) {
    auto id=nextId("Imagem ");
    definition.id=id;
    double scale=std::min(640.0/image.width(),360.0/image.height());
    int w=std::max(1,static_cast<int>(image.width()*scale)),h=std::max(1,static_cast<int>(image.height()*scale));
    auto source=std::make_shared<StillSource>(std::move(image));
    definitions.emplace(source,std::move(definition));
    scenes[selected]->add({id,source,(640-w)/2,(360-h)/2,w,h,{}});
    ids[selected].push_back(id);refresh();
}
void addScene() {
    scenes.push_back(std::make_shared<Scene>());ids.emplace_back();selected=static_cast<int>(scenes.size())-1;
    sceneNames.push_back("Cena "+std::to_string(scenes.size()));
    auto name=wide(sceneNames.back());SendMessage(scenesBox,LB_ADDSTRING,0,reinterpret_cast<LPARAM>(name.c_str()));SendMessage(scenesBox,LB_SETCURSEL,selected,0);refresh();
}
Project snapshotProject() {
    Project p;p.recording_fps=chosenRate();p.selected_scene=selected;p.program_scene=programScene;
    p.gain_db=static_cast<int>(SendMessage(GetDlgItem(window,Gain),TBM_GETPOS,0,0));
    p.microphone=SendMessage(GetDlgItem(window,UseMic),BM_GETCHECK,0,0)==BST_CHECKED;
    p.muted=SendMessage(GetDlgItem(window,Mute),BM_GETCHECK,0,0)==BST_CHECKED;
    std::map<std::string,bool> used;
    for(std::size_t n=0;n<scenes.size();++n) {
        SavedScene saved;saved.name=sceneNames.at(n);
        for(const auto& id:ids[n]) {
            const auto& item=scenes[n]->item(id);const auto& definition=definitions.at(item.source);
            if(!used[definition.id]) {p.sources.push_back(definition);used[definition.id]=true;}
            saved.items.push_back({id,definition.id,item.x,item.y,item.width,item.height,item.crop,item.opacity,item.visible});
        }
        p.scenes.push_back(std::move(saved));
    }
    return p;
}
void openProject(const std::filesystem::path& path) {
    if(recorder) throw std::runtime_error("Stop recording before opening a project");
    auto p=load_project(path);
    std::map<std::string,std::shared_ptr<const VideoSource>> sources;
    decltype(definitions) candidateDefinitions;
    for(auto definition:p.sources) {
        std::shared_ptr<const VideoSource> source;
        if(definition.kind==SourceKind::camera) {
            // Reuse an already-open device; a transactional project open must not
            // acquire the same physical device twice.
            for(const auto& entry:definitions) if(entry.second.kind==SourceKind::camera && entry.second.path==definition.path) {source=entry.first;break;}
            if(!source) source=std::make_shared<CameraSource>(wide(definition.path));
        }
        else if(definition.kind==SourceKind::desktop) source=std::make_shared<DesktopSource>();
        else if(definition.kind==SourceKind::image) {
            auto file=std::filesystem::u8path(definition.path);
            if(file.is_relative()) file=std::filesystem::absolute(path).parent_path()/file;
            definition.path=utf8(file);source=std::make_shared<StillSource>(imageFile(file.c_str()));
        } else source=std::make_shared<StillSource>(Frame(1,1,definition.color));
        sources.emplace(definition.id,source);candidateDefinitions.emplace(source,std::move(definition));
    }
    decltype(scenes) candidateScenes;decltype(ids) candidateIds;
    std::vector<std::string> names;std::vector<std::wstring> labels;
    for(const auto& saved:p.scenes) {
        auto scene=std::make_shared<Scene>();std::vector<std::string> keys;
        for(const auto& item:saved.items) {
            auto source=sources.at(item.source);auto frame=source->frame(0);
            if(item.crop.left+item.crop.right>=frame.width() || item.crop.top+item.crop.bottom>=frame.height())
                throw std::runtime_error("Project crop exceeds source dimensions");
            wide(item.id);
            scene->add({item.id,source,item.x,item.y,item.width,item.height,item.crop,item.opacity,item.visible});keys.push_back(item.id);
        }
        labels.push_back(wide(saved.name));names.push_back(saved.name);
        candidateScenes.push_back(std::move(scene));candidateIds.push_back(std::move(keys));
    }
    auto candidateProgram=std::make_unique<Switcher>(640,360,candidateScenes.at(p.program_scene));
    // All decoding and source validation precede replacement of the active project.
    scenes=std::move(candidateScenes);ids=std::move(candidateIds);definitions=std::move(candidateDefinitions);
    sceneNames=std::move(names);program=std::move(candidateProgram);selected=p.selected_scene;programScene=p.program_scene;
    SendMessage(scenesBox,LB_RESETCONTENT,0,0);
    for(const auto& label:labels) SendMessage(scenesBox,LB_ADDSTRING,0,reinterpret_cast<LPARAM>(label.c_str()));
    SendMessage(scenesBox,LB_SETCURSEL,selected,0);
    auto rateIndex=std::find(recordingRates.begin(),recordingRates.end(),p.recording_fps)-recordingRates.begin();
    SendMessage(GetDlgItem(window,RecordingRate),CB_SETCURSEL,rateIndex,0);
    SendMessage(GetDlgItem(window,Gain),TBM_SETPOS,TRUE,p.gain_db);
    SendMessage(GetDlgItem(window,UseMic),BM_SETCHECK,p.microphone?BST_CHECKED:BST_UNCHECKED,0);
    SendMessage(GetDlgItem(window,Mute),BM_SETCHECK,p.muted?BST_CHECKED:BST_UNCHECKED,0);refresh();
}
Item* selectedItem() {auto index=SendMessage(sourcesBox,LB_GETCURSEL,0,0);if(index==LB_ERR) return nullptr;return &scenes[selected]->item(ids[selected].at(static_cast<std::size_t>(index)));}
void loadTransform() {
    auto* item=selectedItem();
    std::array<int,9> values{};
    if(item) values={item->x,item->y,item->width,item->height,item->crop.left,item->crop.top,item->crop.right,item->crop.bottom,static_cast<int>(std::lround(item->opacity*100))};
    for(int n=0;n<9;++n) {
        auto edit=GetDlgItem(window,TransformFirst+n);EnableWindow(edit,item!=nullptr);
        auto value=item?std::to_wstring(values[n]):L"";SetWindowText(edit,value.c_str());
    }
    EnableWindow(GetDlgItem(window,ApplyTransform),item!=nullptr);
}
int field(int id) {
    auto edit=GetDlgItem(window,id);int length=GetWindowTextLengthA(edit);
    if(length<1 || length>12) throw std::invalid_argument("Enter an integer for each transform field");
    char text[16]{};GetWindowTextA(edit,text,sizeof(text));int value=0;
    auto result=std::from_chars(text,text+length,value);
    if(result.ec!=std::errc{} || result.ptr!=text+length) throw std::invalid_argument("Invalid transform integer");
    return value;
}
void pruneDefinitions() {
    std::erase_if(definitions,[](const auto& entry) {
        for(std::size_t n=0;n<scenes.size();++n)
            for(const auto& key:ids[n]) if(scenes[n]->item(key).source==entry.first) return false;
        return true;
    });
}
void refreshCameras() {
    auto available=camera_devices();cameras=std::move(available);
    auto list=GetDlgItem(window,CameraList);SendMessage(list,CB_RESETCONTENT,0,0);
    for(const auto& device:cameras) SendMessage(list,CB_ADDSTRING,0,reinterpret_cast<LPARAM>(device.name.c_str()));
    if(!cameras.empty()) SendMessage(list,CB_SETCURSEL,0,0);
}
void command(int id) {
    if(id==UseMic || id==Mute) return;
    if(id==RefreshCameras) {refreshCameras();return;}
    if(id==AddCamera) {
        auto index=SendMessage(GetDlgItem(window,CameraList),CB_GETCURSEL,0,0);
        if(index==CB_ERR) throw std::runtime_error("Select a camera; use Atualizar cameras to refresh devices");
        const auto& device=cameras.at(static_cast<std::size_t>(index));
        auto path=utf8(std::filesystem::path(device.id));
        std::shared_ptr<const VideoSource> source;
        for(const auto& entry:definitions) if(entry.second.kind==SourceKind::camera && entry.second.path==path) {source=entry.first;break;}
        auto key=nextId("Camera ");
        if(!source) {
            source=std::make_shared<CameraSource>(device.id);
            definitions.emplace(source,SourceDefinition{key,SourceKind::camera,path,{0,0,0,1}});
        }
        auto frame=source->frame(now());double scale=std::min(640.0/frame.width(),360.0/frame.height());
        int w=std::max(1,static_cast<int>(frame.width()*scale)),h=std::max(1,static_cast<int>(frame.height()*scale));
        scenes[selected]->add({key,source,(640-w)/2,(360-h)/2,w,h,{}});
        ids[selected].push_back(key);refresh();SetTimer(window,1,33,nullptr);return;
    }
    if(id==ReconnectCamera) {
        auto* item=selectedItem();if(!item) throw std::runtime_error("Select a camera source");
        auto camera=dynamic_cast<const CameraSource*>(item->source.get());
        if(!camera) throw std::runtime_error("Selected source is not a camera");
        if(recorder) throw std::runtime_error("Stop recording before reconnecting a camera");
        camera->reconnect();SetTimer(window,1,33,nullptr);InvalidateRect(window,nullptr,FALSE);return;
    }
    if(id==SaveProject || id==OpenProject) {
        if(smoke) {
            auto path=smokeAudio?L"gui-audio-project.vts":L"gui-project.vts";
            if(id==SaveProject) save_project(path,snapshotProject());else openProject(path);
            return;
        }
        wchar_t path[32768]={};OPENFILENAME ofn{};ofn.lStructSize=sizeof(ofn);ofn.hwndOwner=window;ofn.lpstrFile=path;ofn.nMaxFile=32768;
        ofn.lpstrFilter=L"Projeto Vision\0*.vts\0";ofn.lpstrDefExt=L"vts";ofn.Flags=OFN_PATHMUSTEXIST|OFN_NOCHANGEDIR;
        if(id==SaveProject) {ofn.Flags|=OFN_OVERWRITEPROMPT;if(GetSaveFileName(&ofn)) save_project(path,snapshotProject());}
        else {ofn.Flags|=OFN_FILEMUSTEXIST;if(GetOpenFileName(&ofn)) openProject(path);}
        return;
    }
    if(id==Record) {
        if(recorder) {stopRecording();return;}
        if(smoke) {startRecording(smokeAudio?L"gui-audio.mp4":L"gui-recording.mp4");return;}
        wchar_t path[32768]={};OPENFILENAME ofn{};ofn.lStructSize=sizeof(ofn);ofn.hwndOwner=window;ofn.lpstrFile=path;ofn.nMaxFile=32768;
        ofn.lpstrFilter=L"Video MP4\0*.mp4\0";ofn.lpstrDefExt=L"mp4";
        ofn.Flags=OFN_PATHMUSTEXIST|OFN_NOCHANGEDIR;
        // The recorder refuses existing files; never silently overwrite a recording.
        if(GetSaveFileName(&ofn)) startRecording(path);
    }
    else if(id==AddScene) addScene();
    else if(id==AddDesktop) {
        auto key=nextId("Tela ");
        auto source=std::make_shared<DesktopSource>();definitions.emplace(source,SourceDefinition{key,SourceKind::desktop,"",{0,0,0,1}});
        scenes[selected]->add({key,source,0,0,640,360,{}});
        ids[selected].push_back(key);refresh();
    }
    else if(id==AddImage) {
        wchar_t path[32768]={};OPENFILENAME ofn{};ofn.lStructSize=sizeof(ofn);ofn.hwndOwner=window;ofn.lpstrFile=path;ofn.nMaxFile=32768;ofn.lpstrFilter=L"Imagens\0*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff\0Todos\0*.*\0";ofn.Flags=OFN_FILEMUSTEXIST|OFN_PATHMUSTEXIST|OFN_NOCHANGEDIR;
        if(GetOpenFileName(&ofn)) addSource(imageFile(path),{"",SourceKind::image,utf8(std::filesystem::absolute(path)),{0,0,0,1}});
    } else if(id==Cut || id==Fade) {program->take(scenes[selected],now(),id==Cut?0:300000000);programScene=selected;}
    else if(auto* item=selectedItem()) {
        const auto key=item->id;
        if(id==ApplyTransform) {
            std::array<int,9> v{};for(int n=0;n<9;++n) v[n]=field(TransformFirst+n);
            if(v[8]<0 || v[8]>100) throw std::invalid_argument("Opacity must be between 0 and 100");
            scenes[selected]->transform(key,v[0],v[1],v[2],v[3],{v[4],v[5],v[6],v[7]},v[8]/100.f,now());
        }
        if(id==LayerUp || id==LayerDown) {
            auto& keys=ids[selected];auto position=std::find(keys.begin(),keys.end(),key)-keys.begin();
            auto target=position+(id==LayerUp?1:-1);
            if(target>=0 && target<static_cast<std::ptrdiff_t>(keys.size())) {
                scenes[selected]->move(key,static_cast<std::size_t>(target));
                std::swap(keys[static_cast<std::size_t>(position)],keys[static_cast<std::size_t>(target)]);
            }
        }
        if(id==Toggle) item->visible=!item->visible;
        if(id==Smaller || id==Larger) {double factor=id==Smaller?.9:1.1;item->width=std::clamp(static_cast<int>(item->width*factor),1,8192);item->height=std::clamp(static_cast<int>(item->height*factor),1,8192);item->x=(640-item->width)/2;item->y=(360-item->height)/2;}
        if(id==Remove) {auto key=item->id;scenes[selected]->remove(key);std::erase(ids[selected],key);pruneDefinitions();}
        refresh();
        auto it=std::find(ids[selected].begin(),ids[selected].end(),key);
        if(it!=ids[selected].end()) SendMessage(sourcesBox,LB_SETCURSEL,it-ids[selected].begin(),0);
        loadTransform();
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
        case WM_CREATE: {
            window=hwnd;
            control(L"STATIC",L"Cenas",0,15,15,180,25);
            scenesBox=control(L"LISTBOX",L"",SceneList,15,40,180,150,LBS_NOTIFY|WS_BORDER|WS_VSCROLL);
            control(L"BUTTON",L"Adicionar cena",AddScene,15,195,180,30);
            control(L"STATIC",L"Fontes da previa",0,15,235,180,25);
            sourcesBox=control(L"LISTBOX",L"",SourceList,15,260,180,120,LBS_NOTIFY|WS_BORDER|WS_VSCROLL);
            control(L"BUTTON",L"Adicionar imagem",AddImage,15,385,180,30);
            control(L"BUTTON",L"Mostrar / ocultar",Toggle,15,420,180,30);
            control(L"BUTTON",L"Remover fonte",Remove,15,455,180,30);
            control(L"BUTTON",L"Diminuir",Smaller,15,490,85,30);control(L"BUTTON",L"Ampliar",Larger,105,490,90,30);
            control(L"BUTTON",L"Capturar tela",AddDesktop,15,525,180,30);
            control(L"STATIC",L"PREVIA",0,220,15,300,25);control(L"STATIC",L"PROGRAMA",0,560,15,300,25);
            control(L"BUTTON",L"Corte",Cut,220,240,150,35);control(L"BUTTON",L"Fade 300 ms",Fade,380,240,150,35);
            control(L"BUTTON",L"Gravar MP4",Record,560,240,320,35);
            control(L"STATIC",L"Desenvolvimento: cenas, imagens e tela. Camera: selecione o dispositivo abaixo. Transmissao pendente. Sem microfone se a caixa estiver desmarcada.",0,220,300,660,50);
            control(L"BUTTON",L"Gravar microfone padrao",UseMic,220,360,260,30,BS_AUTOCHECKBOX);
            control(L"BUTTON",L"Silenciar audio",Mute,500,360,240,30,BS_AUTOCHECKBOX);
            control(L"STATIC",L"Ganho do microfone (-60 a +12 dB)",0,220,405,300,25);
            auto gainSlider=control(TRACKBAR_CLASS,L"",Gain,220,435,300,30,TBS_AUTOTICKS);
            SendMessage(gainSlider,TBM_SETRANGE,TRUE,MAKELPARAM(-60,12));
            SendMessage(gainSlider,TBM_SETPOS,TRUE,smokeAudio?6:0);
            control(L"STATIC",L"Nivel: aguardando gravacao",MeterLabel,540,435,300,30);
            control(L"BUTTON",L"Salvar projeto",SaveProject,220,490,180,30);
            control(L"BUTTON",L"Abrir projeto",OpenProject,420,490,180,30);
            control(L"BUTTON",L"Subir camada",LayerUp,620,490,125,30);
            control(L"BUTTON",L"Descer camada",LayerDown,755,490,125,30);
            const wchar_t* labels[]={L"X",L"Y",L"Largura",L"Altura",L"Corte esq.",L"Corte topo",L"Corte dir.",L"Corte base",L"Opacidade %"};
            for(int n=0;n<9;++n) {
                int x=220+(n%5)*132,y=535+(n/5)*62;
                control(L"STATIC",labels[n],0,x,y,126,20);
                auto edit=control(L"EDIT",L"",TransformFirst+n,x,y+22,120,26,WS_BORDER|ES_AUTOHSCROLL);
                SendMessage(edit,EM_SETLIMITTEXT,12,0);
            }
            control(L"BUTTON",L"Aplicar",ApplyTransform,748,619,130,30);
            control(L"COMBOBOX",L"",CameraList,220,665,330,180,CBS_DROPDOWNLIST|WS_VSCROLL);
            control(L"BUTTON",L"Atualizar cameras",RefreshCameras,560,665,160,28);
            control(L"BUTTON",L"Adicionar camera",AddCamera,730,665,150,28);
            control(L"BUTTON",L"Reconectar fonte",ReconnectCamera,220,705,180,28);
            control(L"STATIC",L"Taxa de gravacao",0,430,705,160,25);
            auto rate=control(L"COMBOBOX",L"",RecordingRate,600,705,150,160,CBS_DROPDOWNLIST);
            for(int fps:recordingRates) {auto label=std::to_wstring(fps)+L" fps";SendMessage(rate,CB_ADDSTRING,0,reinterpret_cast<LPARAM>(label.c_str()));}
            SendMessage(rate,CB_SETCURSEL,2,0);
            addScene();program=std::make_unique<Switcher>(640,360,scenes[0]);SetTimer(hwnd,1,33,nullptr);return 0;}
        case WM_COMMAND:
            if(LOWORD(wp)==SceneList && HIWORD(wp)==LBN_SELCHANGE) {auto s=SendMessage(scenesBox,LB_GETCURSEL,0,0);if(s!=LB_ERR) {selected=static_cast<int>(s);refresh();}}
            else if(LOWORD(wp)==SourceList && HIWORD(wp)==LBN_SELCHANGE) loadTransform();
            else if(HIWORD(wp)==BN_CLICKED) command(LOWORD(wp));return 0;
        case WM_TIMER:
            if(smoke) {
                if(smokeStep==0) {addSource(Frame(1,1,{1,0,0,1}),{"",SourceKind::solid,"",{1,0,0,1}});SendMessage(hwnd,WM_COMMAND,Cut,0);verify(program->render(now()).at(320,180).r==1);SendMessage(hwnd,WM_COMMAND,Record,0);SendMessage(hwnd,WM_COMMAND,AddScene,0);addSource(Frame(1,1,{0,0,1,1}),{"",SourceKind::solid,"",{0,0,1,1}});SendMessage(hwnd,WM_COMMAND,Fade,0);}
                if(smokeAudio && smokeStep==40) SendMessage(GetDlgItem(hwnd,Mute),BM_SETCHECK,BST_CHECKED,0);
                if(smokeStep==(smokeAudio?60:20)) {captureRecording(now());SendMessage(hwnd,WM_COMMAND,Record,0);verify(program->render(now()).at(320,180).b==1);SendMessage(hwnd,WM_COMMAND,SaveProject,0);auto savedState=encode_project(snapshotProject());SendMessage(hwnd,WM_COMMAND,Toggle,0);verify(program->render(now()).at(320,180).a==0);SendMessage(hwnd,WM_COMMAND,Toggle,0);SendMessage(hwnd,WM_COMMAND,Remove,0);verify(ids[selected].empty());SendMessage(hwnd,WM_COMMAND,OpenProject,0);verify(encode_project(snapshotProject())==savedState);verify(program->render(now()).at(320,180).b==1);
                    auto before=encode_project(snapshotProject());std::ofstream("invalid-project.vts")<<"VISION_PROJECT 99";
                    bool rejected=false;try {openProject(L"invalid-project.vts");}catch(const std::exception&) {rejected=true;}
                    verify(rejected && encode_project(snapshotProject())==before);
                    SetWindowText(GetDlgItem(hwnd,TransformFirst),L"320");
                    SetWindowText(GetDlgItem(hwnd,TransformFirst+2),L"320");
                    SetWindowText(GetDlgItem(hwnd,TransformFirst+8),L"50");
                    SendMessage(hwnd,WM_COMMAND,ApplyTransform,0);
                    auto transformed=program->render(now());verify(transformed.at(10,180).a==0 && transformed.at(400,180).a==.5f);
                    addSource(Frame(1,1,{1,0,0,1}),{"",SourceKind::solid,"",{1,0,0,1}});
                    verify(program->render(now()).at(400,180).r==1);
                    SendMessage(hwnd,WM_COMMAND,LayerDown,0);
                    auto layered=program->render(now());verify(layered.at(400,180).r==.5f && layered.at(400,180).b==.5f);
                    SendMessage(hwnd,WM_COMMAND,SaveProject,0);SendMessage(hwnd,WM_COMMAND,OpenProject,0);
                    verify(program->render(now()).at(400,180).b==.5f);
                    std::ofstream("gui-smoke.txt")<<"PASS: window, scene creation, cut, fade, visibility, source removal, MP4 start/stop, project restore and failed-open preservation\n";DestroyWindow(hwnd);return 0;}
                ++smokeStep;
            }
            captureRecording(now());
            InvalidateRect(hwnd,nullptr,FALSE);return 0;
        case WM_PAINT: {PAINTSTRUCT ps{};auto dc=BeginPaint(hwnd,&ps);try {if(program) {draw(dc,scenes[selected]->render(640,360,now()),220,45,320,180);draw(dc,program->render(now()),560,45,320,180);}}catch(...) {EndPaint(hwnd,&ps);KillTimer(hwnd,1);throw;}EndPaint(hwnd,&ps);return 0;}
        case WM_CLOSE: stopRecording();DestroyWindow(hwnd);return 0;
        case WM_DESTROY: recorder.reset();KillTimer(hwnd,1);program.reset();scenes.clear();PostQuitMessage(0);return 0;
        }
    }catch(const std::exception& e) {
        // An output failure ends this session; do not retry partial samples.
        if(recorder) {try {stopRecording();}catch(...) {}}
        if(smoke) {std::ofstream("gui-smoke.txt")<<"FAIL: "<<e.what();PostQuitMessage(1);}
        else MessageBoxA(hwnd,e.what(),"Vision Track Studio",MB_OK|MB_ICONERROR);
        if(msg==WM_CREATE) return -1;
    }
    return DefWindowProc(hwnd,msg,wp,lp);
}
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE,PWSTR cmd,int show) {
    smokeAudio=std::wstring(cmd).find(L"--self-test-gui-audio")!=std::wstring::npos;
    smoke=std::wstring(cmd).find(L"--self-test-gui")!=std::wstring::npos;
    if(FAILED(CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED))) return 1;
    if(FAILED(MFStartup(MF_VERSION))) {CoUninitialize();return 1;}
    INITCOMMONCONTROLSEX common{sizeof(INITCOMMONCONTROLSEX),ICC_BAR_CLASSES};
    if(!InitCommonControlsEx(&common)) {MFShutdown();CoUninitialize();return 1;}
    WNDCLASS cls{};cls.lpfnWndProc=proc;cls.hInstance=instance;cls.lpszClassName=L"VisionIndependentStudio";cls.hbrBackground=reinterpret_cast<HBRUSH>(COLOR_WINDOW+1);cls.hCursor=LoadCursor(nullptr,IDC_ARROW);
    if(!RegisterClass(&cls)) {MFShutdown();CoUninitialize();return 1;}
    HWND main=CreateWindow(cls.lpszClassName,L"Vision Track Studio - desenvolvimento independente",WS_OVERLAPPEDWINDOW,CW_USEDEFAULT,CW_USEDEFAULT,930,790,nullptr,nullptr,instance,nullptr);
    if(!main) {MFShutdown();CoUninitialize();return 1;}ShowWindow(main,show);
    MSG message{};int status;
    while((status=GetMessage(&message,nullptr,0,0))>0) {TranslateMessage(&message);DispatchMessage(&message);}
    MFShutdown();CoUninitialize();return status<0?1:static_cast<int>(message.wParam);
}
