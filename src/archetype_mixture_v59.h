#pragma once
#include <algorithm>
namespace Sonicraft::AIStrings {
struct ArchetypeMixtureGateV59 {
    float mixtureConfidence=0.f;
    float componentWeight=0.f;
    float componentTrust=1.f;
};
inline bool mixtureComponentAllowedV59(ArchetypeMixtureGateV59 g) noexcept {
    return g.mixtureConfidence>=.42f && g.componentWeight>=.08f && g.componentTrust>.30f;
}
inline bool mixtureOnlyTop1AllowedV59() noexcept { return false; }
inline int maxMixtureComponentsV59() noexcept { return 3; }
inline float mixtureNoLocalConfidenceCapV59() noexcept { return .66f; }
} // namespace Sonicraft::AIStrings
