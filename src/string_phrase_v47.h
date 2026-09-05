#pragma once
#include <algorithm>
#include <cmath>

namespace Sonicraft::AIStrings {

inline float phraseEnergyArcV47(float u,float apex=.62f) noexcept {
    u=std::clamp(u,0.f,1.f);apex=std::clamp(apex,.05f,.95f);
    auto smooth=[](float x){x=std::clamp(x,0.f,1.f);return x*x*(3.f-2.f*x);};
    if(u<=apex)return .90f+.18f*smooth(u/apex);
    return 1.08f-.20f*smooth((u-apex)/(1.f-apex));
}

inline float phraseVibratoRateHzV47(float energy01) noexcept {
    return 4.65f+1.05f*std::clamp(energy01,0.f,1.f);
}

inline float phraseBowReserveV47(float reserve,float noteBeats,float pressure,bool bowChange) noexcept {
    if(bowChange)reserve=1.f;
    const float consume=std::max(0.f,noteBeats)*(.11f+.16f*std::clamp(pressure,0.f,1.f));
    return std::clamp(reserve-consume,0.f,1.f);
}

} // namespace Sonicraft::AIStrings
