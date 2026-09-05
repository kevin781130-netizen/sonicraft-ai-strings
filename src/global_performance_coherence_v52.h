#pragma once
#include <algorithm>

namespace Sonicraft::AIStrings {

struct GlobalCoherenceDecisionV52 {
    float score=100.f;
    float maxEdgeExcess=0.f;
};

inline bool globalCoherencePassV52(GlobalCoherenceDecisionV52 d) noexcept {
    return d.score>=82.f && d.maxEdgeExcess<=1.45f;
}

inline bool globalPairVerifyPassV52(float mergedOverall,float dOverall,
                                    float mergedSafety,float dSafety) noexcept {
    return mergedOverall>=dOverall-.025f && mergedSafety>=dSafety-.04f;
}

inline float coherenceAudioDropLimitV52() noexcept { return .075f; }

} // namespace Sonicraft::AIStrings
