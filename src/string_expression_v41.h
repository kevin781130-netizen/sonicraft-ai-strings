#pragma once
#include <algorithm>
#include <cstdint>
#include <cmath>

namespace Sonicraft::AIStrings {

// v4.1 4x4 String Voice Bus.
// Channels 1..4 remain the legacy Q4 lanes. Extra channels add three independent
// expression voices to each string part without changing old projects.
inline int stringPartForMidiChannel(int ch) noexcept {
    if(ch>=0 && ch<4) return ch;
    if(ch>=4 && ch<=6) return 0;   // Vln I voices 2..4
    if(ch>=7 && ch<=9) return 1;   // Vln II voices 2..4
    if(ch>=10 && ch<=12) return 2; // Viola voices 2..4
    if(ch>=13 && ch<=15) return 3; // Cello voices 2..4
    return -1;
}
inline int encodeShadowStringPart(int part,int lane) noexcept {
    return lane<0 ? std::clamp(part,0,3) : ((std::clamp(part,0,3)&3) | ((std::clamp(lane,0,15)+1)<<2));
}
inline int stringVoiceIndexForMidiChannel(int ch) noexcept {
    if(ch>=0 && ch<4) return 0;
    if(ch>=4 && ch<=6) return ch-3;
    if(ch>=7 && ch<=9) return ch-6;
    if(ch>=10 && ch<=12) return ch-9;
    if(ch>=13 && ch<=15) return ch-12;
    return -1;
}

enum StringExpressionModifier : std::uint8_t {
    kExprAccent     = 1u<<0,
    kExprLegato     = 1u<<1,
    kExprTenuto     = 1u<<2,
    kExprExpressive = 1u<<3,
};

inline std::uint8_t expressionStackFromNormalized(float v) noexcept {
    return static_cast<std::uint8_t>(std::clamp(int(std::lround(std::clamp(v,0.f,1.f)*15.f)),0,15));
}
inline float expressionStackToNormalized(std::uint8_t mask) noexcept {
    return static_cast<float>(mask&0x0Fu)/15.f;
}
inline std::uint8_t packArticulationExpression(int baseArt,std::uint8_t stack) noexcept {
    return static_cast<std::uint8_t>((std::clamp(baseArt,0,15)&0x0F)|((stack&0x0F)<<4));
}
inline int unpackBaseArticulation(int packed) noexcept { return packed&0x0F; }
inline std::uint8_t unpackExpressionStack(int packed) noexcept { return static_cast<std::uint8_t>((packed>>4)&0x0F); }

template<class C>
inline C applyStringExpressionModifiers(C c,std::uint8_t stack) noexcept {
    if(stack&kExprAccent){
        c.attack=std::clamp(c.attack+.18f,0.f,1.f);
        c.tightness=std::clamp(c.tightness+.08f,0.f,1.f);
        c.dyn=std::clamp(c.dyn+.035f,0.f,1.f);
    }
    if(stack&kExprLegato){
        c.leg=1.f;
        c.transition=std::clamp(c.transition-.10f,0.f,1.f);
    }
    if(stack&kExprTenuto){
        c.tightness=std::clamp(c.tightness-.16f,0.f,1.f);
        c.transition=std::clamp(c.transition-.04f,0.f,1.f);
    }
    if(stack&kExprExpressive){
        c.attack=std::clamp(c.attack-.10f,0.f,1.f);
        c.vib=std::clamp(c.vib+.10f,0.f,1.f);
        c.exp=std::clamp(c.exp+.045f,0.f,1.f);
    }
    return c;
}

} // namespace Sonicraft::AIStrings
