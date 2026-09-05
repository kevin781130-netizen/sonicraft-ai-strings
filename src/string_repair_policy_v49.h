#pragma once
#include <algorithm>

namespace Sonicraft::AIStrings {

struct RepairPolicyV49 {
    float smoothing=1.f;
    float bowRelief=1.f;
    float transition=1.f;
    float ensembleTightness=1.f;
    float expressiveApex=1.f;
};

inline float clampRepairPolicyV49(float x) noexcept {
    return std::clamp(x,.65f,1.35f);
}

inline bool repairLearningGateV49(float margin,float safety,float overall,bool stale=false) noexcept {
    return !stale && margin>=.025f && safety>=.35f && overall>=.35f;
}

inline RepairPolicyV49 repairTargetV49(char slot) noexcept {
    if(slot=='A')return {.84f,.90f,.90f,.92f,.90f};
    if(slot=='B')return {1.18f,1.17f,1.18f,1.18f,.88f};
    if(slot=='C')return {1.02f,.95f,1.00f,.94f,1.22f};
    return {.78f,.80f,.82f,.86f,.86f}; // D Original wins -> back away from repair strength.
}

inline RepairPolicyV49 updateRepairPolicyV49(RepairPolicyV49 p,char winner,float margin) noexcept {
    if(!repairLearningGateV49(margin,1.f,1.f,false))return p;
    const auto t=repairTargetV49(winner);
    const float a=std::min(.16f,.035f+std::max(0.f,margin)*.55f);
    p.smoothing=clampRepairPolicyV49(p.smoothing+a*(t.smoothing-p.smoothing));
    p.bowRelief=clampRepairPolicyV49(p.bowRelief+a*(t.bowRelief-p.bowRelief));
    p.transition=clampRepairPolicyV49(p.transition+a*(t.transition-p.transition));
    p.ensembleTightness=clampRepairPolicyV49(p.ensembleTightness+a*(t.ensembleTightness-p.ensembleTightness));
    p.expressiveApex=clampRepairPolicyV49(p.expressiveApex+a*(t.expressiveApex-p.expressiveApex));
    return p;
}

} // namespace Sonicraft::AIStrings
