#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
namespace Sonicraft::AIStrings {
struct PreferenceAutoCompGateV39 { int take=-1; bool commit=false; float margin=0.f,safety=0.f; };
inline PreferenceAutoCompGateV39 evaluatePreferenceAutoCompV39(bool personalEnabled,float profileConfidence,float minConfidence,float minMargin,float safetyFloor,uint8_t validMask,const std::array<float,4>& personal,const std::array<float,4>& safety) noexcept {
    float top=-1.f,second=-1.f;int best=-1;
    for(int i=0;i<4;++i){if(!(validMask&(1u<<i)))continue;const float s=personal[i];if(s>top){second=top;top=s;best=i;}else if(s>second)second=s;}
    PreferenceAutoCompGateV39 d{};d.take=best;d.margin=top-std::max(0.f,second);d.safety=best>=0?safety[best]:0.f;
    d.commit=personalEnabled&&best>=0&&profileConfidence>=minConfidence&&d.margin>=minMargin&&d.safety>=safetyFloor;
    return d;
}
}
