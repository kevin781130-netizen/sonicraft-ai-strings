#pragma once
#include <algorithm>

namespace Sonicraft::AIStrings {

struct CandidateUtilityGateV55 {
    float confidence=0.f;
    float predictedMargin=0.f;
    float memoryEvidence=0.f;
};

inline bool highConfidenceTop1V55(CandidateUtilityGateV55 g) noexcept {
    return g.confidence>=.72f && g.predictedMargin>=.12f && g.memoryEvidence>=3.f;
}

inline bool mediumConfidenceTop2V55(CandidateUtilityGateV55 g) noexcept {
    return g.confidence>=.48f && g.memoryEvidence>=1.5f;
}

inline bool candidateUtilityEscalateV55(float audioMargin,bool predictorWinnerAgrees,
                                        float winnerSafety,float winnerOverall) noexcept {
    return audioMargin<.025f || !predictorWinnerAgrees || winnerSafety<.35f || winnerOverall<.35f;
}

inline bool skippedCandidateMayLearnV55() noexcept { return false; }
inline bool originalDAlwaysRenderedV55() noexcept { return true; }

} // namespace Sonicraft::AIStrings
