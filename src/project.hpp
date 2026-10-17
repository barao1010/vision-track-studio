#pragma once
#include "core.hpp"
#include <filesystem>
namespace vision {
enum class SourceKind { image=0, desktop=1, solid=2 };
struct SourceDefinition {
    std::string id;
    SourceKind kind=SourceKind::solid;
    std::string path; // UTF-8; relative paths resolve against the project directory
    Pixel color{0,0,0,1};
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
    int selected_scene=0,program_scene=0,gain_db=0;
    bool microphone=false,muted=false;
};
void validate_project(const Project& project);
std::string encode_project(const Project& project);
Project decode_project(const std::string& text);
Project load_project(const std::filesystem::path& path);
void save_project(const std::filesystem::path& path,const Project& project);
}
