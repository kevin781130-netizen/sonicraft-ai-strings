#pragma once
#include <algorithm>

namespace Sonicraft::AIStrings {

enum class ShadowLoopStopV50 { Continue, LowMargin, SafetyFloor, LowOverall, StalePolicy, RoundCap, RenderFailure };

inline ShadowLoopStopV50 shadowLoopGateV50(float margin,float safety,float overall,bool stale,int round,int maxRound) noexcept {
    if(stale)return ShadowLoopStopV50::StalePolicy;
    if(safety<.35f)return ShadowLoopStopV50::SafetyFloor;
    if(overall<.35f)return ShadowLoopStopV50::LowOverall;
    if(margin<.025f)return ShadowLoopStopV50::LowMargin;
    if(round>=std::max(1,maxRound))return ShadowLoopStopV50::RoundCap;
    return ShadowLoopStopV50::Continue;
}

inline bool shadowLoopMayLearnV50(ShadowLoopStopV50 s) noexcept {
    return s==ShadowLoopStopV50::Continue || s==ShadowLoopStopV50::RoundCap;
}

inline int shadowLoopMaxRoundsV50() noexcept { return 6; }

} // namespace Sonicraft::AIStrings
