#include <windows.h>
#include "windows_microphone.hpp"
#include <iostream>
#include <set>
#include <stdexcept>
int main() {
    if(FAILED(CoInitializeEx(nullptr,COINIT_MULTITHREADED))) return 1;
    int result=0;
    try {
        auto devices=vision::microphone_devices();std::set<std::wstring> identities;
        for(const auto& device:devices) {
            if(device.id.empty() || device.name.empty() || !identities.insert(device.id).second)
                throw std::runtime_error("Invalid/duplicate microphone descriptor");
        }
        bool rejected=false;
        try {vision::WindowsMicrophone missing(L"vision-contract-nonexistent-endpoint");}
        catch(const std::exception& error) {
            rejected=std::string(error.what()).find("Open selected microphone (no fallback)")!=std::string::npos;
        }
        if(!rejected) throw std::runtime_error("Missing endpoint must fail without default fallback");
        std::cout<<"PASS: capture endpoint enumeration and explicit missing-ID failure; no physical microphone activated\n";
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';result=1;}
    CoUninitialize();return result;
}
