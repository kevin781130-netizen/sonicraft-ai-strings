#pragma once
#include <algorithm>
#include <array>

namespace Sonicraft::AIStrings {

struct CriticDimensionsV48 {
    float bowReserve=100.f;
    float transition=100.f;
    float vibrato=100.f;
    float dynamicsArc=100.f;
    float gestureSpikes=100.f;
    float ensembleAlignment=100.f;
};

inline float weightedCriticScoreV48(const CriticDimensionsV48& d) noexcept {
    return std::clamp(
        d.bowReserve*.20f+d.transition*.20f+d.vibrato*.15f+
        d.dynamicsArc*.15f+d.gestureSpikes*.15f+d.ensembleAlignment*.15f,
        0.f,100.f);
}

inline float repairBlendV48(char slot) noexcept {
    return slot=='A' ? .24f : (slot=='B' ? .52f : (slot=='C' ? .36f : 0.f));
}

inline bool structuralRepairCanAutoCommitV48() noexcept {
    // Structural critic must never replace the audio-aware judge.
    return false;
}

} // namespace Sonicraft::AIStrings
