#pragma once
#include <algorithm>

namespace Sonicraft::AIStrings {

inline bool selectivePhraseFallbackV51(float coverage,int windows,float winnerMargin,
                                       float safety,float overall) noexcept {
    if(coverage>.55f || windows<=0 || windows>6)return true;
    if(winnerMargin<.025f)return true;
    if(safety<.35f || overall<.35f)return true;
    return false;
}

inline float selectiveRenderFractionV51(float localizedContextSeconds,float songSeconds,
                                        bool includeFinalFullRender=true) noexcept {
    const float song=std::max(.001f,songSeconds);
    const float localFour=4.f*std::max(0.f,localizedContextSeconds)/song;
    const float total=localFour+(includeFinalFullRender?1.f:0.f);
    return total/4.f; // relative to one v5.0 round of four full renders
}

} // namespace Sonicraft::AIStrings
