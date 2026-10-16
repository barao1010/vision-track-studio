#include "media.hpp"
#include <bit>
#include <cmath>
#include <iostream>
#include <iterator>
#include <stdexcept>
using namespace vision;
void check(bool ok) {if(!ok) throw std::runtime_error("Media contract failed");}
template<class F> void rejects(F fn) {bool fail=false;try{fn();}catch(const std::exception&){fail=true;}check(fail);}
int main(int argc,char** argv) {
    check(argc==2);
    const std::filesystem::path base=argv[1];
    check(!std::filesystem::exists(base));std::filesystem::create_directories(base);
    const auto source=base/"source.ppm";
    {std::ofstream out(source,std::ios::binary);out<<"P6\n# comment\n2 1\n255\n";const char data[]={10,32,35,0,127,static_cast<char>(255)};out.write(data,6);}
    const auto image=read_ppm(source);check(image.width()==2 && image.height()==1);check(image.at(0,0).r>0);check(image.at(1,0).b==1);
    {std::ofstream out(base/"truncated.ppm");out<<"P6\n2 1\n255\nx";}
    rejects([&]{read_ppm(base/"truncated.ppm");});
    RawRecorder recorder(base/"output",2,1,30,48000);
    AudioBlock samples{0,2,std::vector<float>(3200,.25f)};
    auto invalid=samples;invalid.start_sample=1;
    rejects([&]{recorder.append(image,invalid);});
    recorder.append(image,samples);recorder.finish();recorder.finish();
    rejects([&]{recorder.append(image,samples);});
    rejects([&]{RawRecorder collision(base/"output",2,1,30,48000);});
    check(std::filesystem::file_size(base/"output/video.rgb")==6);
    check(std::filesystem::file_size(base/"output/audio.f32le")==12800);
    {std::ifstream in(base/"output/video.rgb",std::ios::binary);std::vector<unsigned char> b((std::istreambuf_iterator<char>(in)),{});check(b==std::vector<unsigned char>({10,32,35,0,127,255}));}
    {std::ifstream in(base/"output/audio.f32le",std::ios::binary);unsigned char b[4];in.read(reinterpret_cast<char*>(b),4);check(b[0]==0 && b[1]==0 && b[2]==128 && b[3]==62);}
    std::filesystem::remove_all(base);
    std::cout<<"PASS: image loading, color roundtrip, recorder timeline, sample bytes, collision rejection\n";
}
