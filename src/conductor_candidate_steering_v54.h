#pragma once
#include <array>
#include <algorithm>

namespace Sonicraft::AIStrings {

enum class CandidateSectionV54 { Intro, Build, Sustain, Climax, Release, Resolution };

struct CandidateBudgetV54 {
    bool A=true, B=true, C=true, D=true;
};

inline CandidateBudgetV54 primaryBudgetV54(CandidateSectionV54 s) noexcept {
    if(s==CandidateSectionV54::Climax) return {false,true,true,true};
    if(s==CandidateSectionV54::Intro ||
       s==CandidateSectionV54::Release ||
       s==CandidateSectionV54::Resolution) return {true,true,false,true};
    return {true,true,true,true};
}

inline bool escalateDeferredCandidateV54(float margin) noexcept {
    return margin < .025f;
}

inline float clampSteeringV54(float x) noexcept {
    return std::clamp(x,0.f,1.f);
}

inline bool originalDIsSteeredV54() noexcept { return false; }

} // namespace Sonicraft::AIStrings
