#pragma once
#include <algorithm>
#include <cstdint>
namespace Sonicraft::AIStrings {
enum StringGestureOpcodeV45 : std::uint8_t { kGestureAmount=122 };
inline float gestureMicroPitchFromNormalizedV45(float v) noexcept {
    return (std::clamp(v,0.f,1.f)-.5f)*100.f; // +/-50 cents
}
}
