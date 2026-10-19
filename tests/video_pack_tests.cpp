#include "video_pack.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace vision;
void check(bool condition) {if(!condition) throw std::runtime_error("Video packing contract failed");}
int main() {
    int previous=-1;
    for(int i=0;i<=1000000;++i) {
        const float linear=i/1000000.f;
        const int reference=static_cast<int>(std::lround(255*(linear<=.0031308f?12.92f*linear:1.055f*std::pow(linear,1.f/2.4f)-.055f)));
        const int value=linear_to_srgb8(linear);check(std::abs(value-reference)<=1 && value>=previous);previous=value;
    }
    check(linear_to_srgb8(-100)==0 && linear_to_srgb8(100)==255);
    check(linear_to_srgb8(0)==0 && linear_to_srgb8(1)==255);
    Frame f(2,2);f.at(0,0)={1,0,0,1};f.at(1,0)={0,1,0,1};f.at(0,1)={0,0,1,1};f.at(1,1)={1,1,1,.5f};
    const auto bytes=pack_bgrx(f);
    check(bytes.size()==16 && bytes[0]==0 && bytes[2]==255 && bytes[5]==255 && bytes[8]==255 && bytes[10]==0);
    check(bytes[12]==188 && bytes[13]==188 && bytes[14]==188 && bytes[15]==0);
    for(float invalid:{std::numeric_limits<float>::infinity(),std::numeric_limits<float>::quiet_NaN()}) {
        bool rejected=false;try {linear_to_srgb8(invalid);}catch(const std::invalid_argument&){rejected=true;}check(rejected);
        f.at(0,0).a=invalid;rejected=false;try {pack_bgrx(f);}catch(const std::invalid_argument&){rejected=true;}check(rejected);
    }
    std::cout<<"PASS: million-point analytic sRGB error <=1 code, monotonicity, endpoints, BGRX order/alpha and malformed pixels\n";
}
