#pragma once
#include <algorithm>

namespace Sonicraft::AIStrings {

struct CounterfactualAuditStateV56 {
    int audits=0;
    int falsePrunes=0;
    int cleanStreak=0;
    bool disabled=false;
};

inline float falsePruneRateV56(CounterfactualAuditStateV56 s) noexcept {
    return s.audits>0 ? static_cast<float>(s.falsePrunes)/static_cast<float>(s.audits) : 0.f;
}

inline int auditIntervalV56(CounterfactualAuditStateV56 s) noexcept {
    if(s.disabled) return 1;
    const auto r=falsePruneRateV56(s);
    if(s.audits>=3 && r>=.20f) return 4;
    if(s.audits>=3 && r>=.10f) return 6;
    return 12;
}

inline bool falsePruneV56(float preOverall,float fullOverall,float fullSafety,bool fullWinnerWasPruned) noexcept {
    return fullWinnerWasPruned && fullOverall-preOverall>=.025f && fullSafety>=.35f && fullOverall>=.35f;
}

inline bool disableZeroRenderV56(CounterfactualAuditStateV56 s) noexcept {
    return s.audits>=4 && falsePruneRateV56(s)>=.25f;
}

inline bool recoverZeroRenderV56(CounterfactualAuditStateV56 s) noexcept {
    return s.disabled && s.cleanStreak>=4;
}

} // namespace Sonicraft::AIStrings
