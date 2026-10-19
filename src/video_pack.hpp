#pragma once
#include "core.hpp"
namespace vision {
// Quantized transfer function; maximum one 8-bit code difference from analytic sRGB.
std::uint8_t linear_to_srgb8(float linear);
// Top-down BGRX, composited over black. Rejects nonfinite input.
std::vector<std::uint8_t> pack_bgrx(const Frame& frame);
}
