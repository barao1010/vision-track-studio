#include "project.hpp"
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <random>
#include <set>
#include <sstream>
#include <stdexcept>
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#endif
namespace vision {
namespace {
constexpr std::size_t max_bytes=8*1024*1024;
void require(bool ok) {if(!ok) throw std::invalid_argument("Invalid or unsupported Vision project");}
void string_ok(const std::string& value,std::size_t max,bool empty=false) {require((empty || !value.empty()) && value.size()<=max && value.find('\0')==std::string::npos);}
bool unit(float n) {return std::isfinite(n) && n>=0 && n<=1;}
std::size_t count(std::istream& in,std::size_t max) {std::size_t n=0;require(bool(in>>n) && n<=max);return n;}
struct Temporary {
    std::filesystem::path directory;
    ~Temporary() {std::error_code ec;std::filesystem::remove(directory/"project.tmp",ec);std::filesystem::remove(directory,ec);}
};
}
void validate_project(const Project& p) {
    require(p.sources.size()<=1000 && !p.scenes.empty() && p.scenes.size()<=100);
    require(p.selected_scene>=0 && static_cast<std::size_t>(p.selected_scene)<p.scenes.size());
    require(p.program_scene>=0 && static_cast<std::size_t>(p.program_scene)<p.scenes.size());
    require(p.gain_db>=-60 && p.gain_db<=12);
    std::set<std::string> sources,cameras;
    for(const auto& s:p.sources) {
        string_ok(s.id,128);string_ok(s.path,32768,true);require(sources.insert(s.id).second);
        require(s.kind==SourceKind::image || s.kind==SourceKind::desktop || s.kind==SourceKind::solid || s.kind==SourceKind::camera);
        require((s.kind!=SourceKind::image && s.kind!=SourceKind::camera) || !s.path.empty());
        if(s.kind==SourceKind::camera) require(cameras.insert(s.path).second);
        require(unit(s.color.r) && unit(s.color.g) && unit(s.color.b) && unit(s.color.a));
    }
    std::size_t total=0;
    for(const auto& scene:p.scenes) {
        string_ok(scene.name,512);total+=scene.items.size();require(total<=10000);
        std::set<std::string> ids;
        for(const auto& i:scene.items) {
            string_ok(i.id,128);require(ids.insert(i.id).second && sources.contains(i.source));
            require(i.width>0 && i.height>0 && i.width<=16384 && i.height<=16384);
            require(i.crop.left>=0 && i.crop.top>=0 && i.crop.right>=0 && i.crop.bottom>=0);
            require(i.crop.left<=16384 && i.crop.top<=16384 && i.crop.right<=16384 && i.crop.bottom<=16384);
            require(unit(i.opacity));
        }
    }
}
std::string encode_project(const Project& p) {
    validate_project(p);std::ostringstream out;out.imbue(std::locale::classic());out<<std::setprecision(std::numeric_limits<float>::max_digits10);
    out<<"VISION_PROJECT 1\n"<<p.selected_scene<<' '<<p.program_scene<<' '<<p.gain_db<<' '<<p.microphone<<' '<<p.muted<<'\n'<<p.sources.size()<<'\n';
    for(const auto& s:p.sources) out<<std::quoted(s.id)<<' '<<static_cast<int>(s.kind)<<' '<<std::quoted(s.path)<<' '<<s.color.r<<' '<<s.color.g<<' '<<s.color.b<<' '<<s.color.a<<'\n';
    out<<p.scenes.size()<<'\n';
    for(const auto& scene:p.scenes) {
        out<<std::quoted(scene.name)<<' '<<scene.items.size()<<'\n';
        for(const auto& i:scene.items) out<<std::quoted(i.id)<<' '<<std::quoted(i.source)<<' '<<i.x<<' '<<i.y<<' '<<i.width<<' '<<i.height<<' '<<i.crop.left<<' '<<i.crop.top<<' '<<i.crop.right<<' '<<i.crop.bottom<<' '<<i.opacity<<' '<<i.visible<<'\n';
    }
    auto text=out.str();require(text.size()<=max_bytes);return text;
}
Project decode_project(const std::string& text) {
    require(text.size()<=max_bytes);std::istringstream in(text);in.imbue(std::locale::classic());
    std::string magic;int version=0;require(bool(in>>magic>>version) && magic=="VISION_PROJECT" && version==1);
    Project p;require(bool(in>>p.selected_scene>>p.program_scene>>p.gain_db>>p.microphone>>p.muted));
    auto sources=count(in,1000);
    for(std::size_t n=0;n<sources;++n) {
        SourceDefinition s;int kind=0;require(bool(in>>std::quoted(s.id)>>kind>>std::quoted(s.path)>>s.color.r>>s.color.g>>s.color.b>>s.color.a));
        s.kind=static_cast<SourceKind>(kind);p.sources.push_back(std::move(s));
    }
    auto scenes=count(in,100);std::size_t total=0;
    for(std::size_t n=0;n<scenes;++n) {
        SavedScene s;require(bool(in>>std::quoted(s.name)));auto items=count(in,10000);total+=items;require(total<=10000);
        for(std::size_t j=0;j<items;++j) {
            SavedItem i;require(bool(in>>std::quoted(i.id)>>std::quoted(i.source)>>i.x>>i.y>>i.width>>i.height>>i.crop.left>>i.crop.top>>i.crop.right>>i.crop.bottom>>i.opacity>>i.visible));s.items.push_back(std::move(i));
        }
        p.scenes.push_back(std::move(s));
    }
    in>>std::ws;require(in.eof());validate_project(p);return p;
}
Project load_project(const std::filesystem::path& path) {
    std::ifstream file(path,std::ios::binary);if(!file) throw std::runtime_error("Could not open project");
    std::string text;char buffer[4096];
    while(file.read(buffer,sizeof(buffer)) || file.gcount()) {
        require(text.size()+static_cast<std::size_t>(file.gcount())<=max_bytes);text.append(buffer,static_cast<std::size_t>(file.gcount()));
    }
    if(!file.eof()) throw std::runtime_error("Could not read project");
    return decode_project(text);
}
void save_project(const std::filesystem::path& path,const Project& project) {
    auto text=encode_project(project);auto parent=std::filesystem::absolute(path).parent_path();
    std::random_device random;std::filesystem::path directory;
    for(int attempt=0;attempt<100;++attempt) {
        auto candidate=parent/(".vision-save-"+std::to_string(random())+"-"+std::to_string(random()));
        if(std::filesystem::create_directory(candidate)) {directory=candidate;break;}
    }
    if(directory.empty()) throw std::runtime_error("Could not allocate project temporary file");
    Temporary temporary{directory};auto file=directory/"project.tmp";
    {std::ofstream out(file,std::ios::binary);out.exceptions(std::ios::badbit|std::ios::failbit);out.write(text.data(),static_cast<std::streamsize>(text.size()));out.close();}
#ifdef _WIN32
    if(!MoveFileExW(file.c_str(),path.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)) throw std::runtime_error("Could not replace project file");
#else
    std::filesystem::rename(file,path);
#endif
}
}
