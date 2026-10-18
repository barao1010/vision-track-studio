#pragma once
#include "core.hpp"
#include <filesystem>
namespace vision {
enum class SourceKind { image=0, desktop=1, solid=2, camera=3, browser=4 };
struct SourceDefinition {
    std::string id;
    SourceKind kind=SourceKind::solid;
    std::string path; // UTF-8 image path (relative to project), or camera symbolic link
    Pixel color{0,0,0,1};
    std::string css{};
    int browser_width=640,browser_height=360;
};
struct SavedItem {
    std::string id,source;
    int x=0,y=0,width=1,height=1;
    Crop crop;
    float opacity=1;
    bool visible=true;
};
struct SavedScene { std::string name;std::vector<SavedItem> items; };
struct Project {
    std::vector<SourceDefinition> sources;
    std::vector<SavedScene> scenes;
    int selected_scene=0,program_scene=0,gain_db=0,recording_fps=30,video_kbps=4000,output_height=360;
    bool microphone=false,muted=false;
    std::string microphone_id; // Empty follows default at recording start; otherwise exact endpoint ID.
};
void validate_project(const Project& project);
std::string encode_project(const Project& project);
Project decode_project(const std::string& text);
Project load_project(const std::filesystem::path& path);
void save_project(const std::filesystem::path& path,const Project& project);
}
