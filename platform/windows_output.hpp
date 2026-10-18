#pragma once
#include "output_worker.hpp"
#include <filesystem>
namespace vision {
std::unique_ptr<OutputSink> create_windows_output(const std::filesystem::path& path,bool microphone,bool synthetic_test_audio=false,int fps=30);
}
