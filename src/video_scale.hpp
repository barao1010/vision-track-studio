#pragma once
#include "core.hpp"
namespace vision {
// Bilinear resampling in linear light with premultiplied-alpha interpolation.
Frame scale_frame(const Frame& source,int width,int height);
}
