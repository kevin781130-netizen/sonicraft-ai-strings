#pragma once
#include <algorithm>

namespace Sonicraft::AIStrings {

inline float contextJaccardV57(int intersectionCount,int unionCount) noexcept {
    if(intersectionCount<=0 || unionCount<=0) return 0.f;
    return std::clamp(float(intersectionCount)/float(unionCount),0.f,1.f);
}
inline bool contextTransferAllowedV57(bool sameSectionCharacter,float jaccard,bool donorDisabled) noexcept {
    return sameSectionCharacter && !donorDisabled && jaccard>=.34f;
}
inline float transferredEvidenceV57(float donorEvidence,float similarity,float auditMultiplier,float edgeTrust) noexcept {
    return std::clamp(donorEvidence*similarity*auditMultiplier*edgeTrust*.32f,0.f,4.f);
}
inline bool transferOnlyMayUseTop1V57(float localEvidence) noexcept { return localEvidence>=1.5f; }
inline float falsePruneEdgeTrustV57(float trust,float gain) noexcept {
    const float factor=gain>=.05f ? .56f : .66f;
    return std::max(.15f,trust*factor);
}

} // namespace Sonicraft::AIStrings
