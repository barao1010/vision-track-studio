#include "project.hpp"
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace vision;
void check(bool ok) {if(!ok) throw std::runtime_error("Project contract failed");}
template<class F> void rejects(F fn) {bool rejected=false;try {fn();}catch(const std::exception&) {rejected=true;}check(rejected);}
int main(int argc,char** argv) {
    check(argc==2);std::filesystem::path base=argv[1];check(!std::filesystem::exists(base));std::filesystem::create_directories(base);
    Project p;
    p.sources={{"red",SourceKind::solid,"",{1,0,0,1}},{"logo",SourceKind::image,"images/quoted \"logo\".png",{0,0,0,1}},{"screen",SourceKind::desktop,"",{0,0,0,1}}};
    p.scenes={{"Scene one",{{"layer","red",-30,24,640,360,{1,2,3,4},.37f,false}}},{"Scene two",{{"shared","red",0,0,1,1,{},1,true}}}};
    p.sources.push_back({"camera",SourceKind::camera,"device-symbolic-link",{0,0,0,1}});
    SourceDefinition browser{"web",SourceKind::browser,"https://example.invalid/overlay",{0,0,0,1}};
    browser.css="body { color: white; }";p.sources.push_back(browser);
    p.recording_fps=25;p.video_kbps=8000;p.microphone_id="endpoint-\"saved\"";
    check(decode_project("VISION_PROJECT 4\n0 0 0 0 0 30 4000\n0\n1\n\"Legacy\" 0\n").microphone_id.empty());
    for(auto value:{std::string(32769,'x'),std::string("bad\0id",6)}) {auto invalid=p;invalid.microphone_id=value;rejects([&]{encode_project(invalid);});}
    check(decode_project("VISION_PROJECT 3\n0 0 0 0 0 30\n0\n1\n\"Legacy\" 0\n").video_kbps==4000);
    for(int value:{-1,0,499,50001,2147483647}) {auto invalid=p;invalid.video_kbps=value;rejects([&]{encode_project(invalid);});}
    check(decode_project("VISION_PROJECT 1\n0 0 0 0 0\n0\n1\n\"Legacy\" 0\n").recording_fps==30);
    for(int value:{500,50000}) {auto valid=p;valid.video_kbps=value;check(decode_project(encode_project(valid)).video_kbps==value);}
    p.selected_scene=1;p.gain_db=6;p.microphone=true;
    auto text=encode_project(p);auto roundtrip=decode_project(text);check(encode_project(roundtrip)==text);
    auto file=base/"project.vts";save_project(file,p);check(encode_project(load_project(file))==text);
    p.muted=true;save_project(file,p);check(load_project(file).muted);
    auto invalidRate=p;invalidRate.recording_fps=29;rejects([&]{encode_project(invalidRate);});
    auto bad=p;bad.sources.push_back(bad.sources[0]);rejects([&]{save_project(file,bad);});check(load_project(file).muted);
    bad=p;bad.scenes[0].items[0].source="missing";rejects([&]{encode_project(bad);});
    bad=p;bad.scenes[0].items[0].opacity=std::numeric_limits<float>::quiet_NaN();rejects([&]{encode_project(bad);});
    rejects([&]{decode_project(text+"garbage");});rejects([&]{decode_project(text.substr(0,text.size()/2));});
    rejects([]{decode_project("VISION_PROJECT 2\n");});
    rejects([]{decode_project("VISION_PROJECT 1\n0 0 0 0 0\n999999999\n");});
    rejects([]{decode_project(std::string(8*1024*1024+1,'x'));});
    std::filesystem::create_directory(base/"directory.vts");rejects([&]{save_project(base/"directory.vts",p);});
    check(std::filesystem::is_directory(base/"directory.vts"));
    for(const auto& entry:std::filesystem::directory_iterator(base)) check(entry.path().filename().string().find(".vision-save-")!=0);
    std::filesystem::remove_all(base);
    std::cout<<"PASS: project roundtrip, source identity, transforms/audio, atomic replacement, malformed input and cleanup\n";
}
