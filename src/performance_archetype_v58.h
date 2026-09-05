#pragma once
#include <algorithm>

namespace Sonicraft::AIStrings {

enum class PerformanceArchetypeV58 {
    Intimate, Ballad, Dramatic, Chamber, Cinematic
};

struct ArchetypeGateV58 {
    float classificationConfidence=0.f;
    float edgeTrust=1.f;
    float effectiveEvidence=0.f;
};

inline bool archetypeEvidenceAllowedV58(ArchetypeGateV58 g) noexcept {
    return g.classificationConfidence>=.42f && g.edgeTrust>.30f && g.effectiveEvidence>0.f;
}

inline bool archetypeOnlyTop1AllowedV58() noexcept { return false; }
inline float archetypeNoLocalConfidenceCapV58() noexcept { return .66f; }
inline float archetypeEvidenceScaleV58() noexcept { return .42f; }

} // namespace Sonicraft::AIStrings
