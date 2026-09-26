#pragma once
#include "preview_engine.h"
#include <algorithm>
#include <cstdint>
#include <cmath>

namespace Sonicraft::AIStrings {
// Explicitly opt-in, deterministic performance shaping for the procedural
// previews. The MIDI note, gate, authored CC and keyswitch remain authoritative.
inline PartControl shapeAcousticPerformance(PartControl c,int instrument,int lane,int note,
                                           int previousNote,float velocity,bool smartDynamics,
                                           int retakeTarget,float retakeAmount,float retakeSeed,
                                           bool authorityLock) noexcept {
    if(smartDynamics){
        const float leap=previousNote>=0?std::clamp(float(std::abs(note-previousNote))/24.f,0.f,1.f):0.f;
        const float accent=(std::clamp(velocity,0.f,1.f)-.5f)*.12f+leap*.04f;
        c.dynamics=std::clamp(c.dynamics*(1.f+accent),0.f,1.f);
    }
    if(retakeTarget<1||retakeTarget>7||retakeAmount<=0.f)return c;
    std::uint32_t h=std::uint32_t(std::clamp(retakeSeed,0.f,1.f)*16777215.f)
                    ^std::uint32_t((instrument+1)*2654435761u)
                    ^std::uint32_t((lane+1)*2246822519u)
                    ^std::uint32_t((note+1)*3266489917u);
    h^=h>>16;h*=0x7feb352du;h^=h>>15;h*=0x846ca68bu;h^=h>>16;
    const float signedVariation=float(h&0xffffu)/32767.5f-1.f;
    const float depth=std::clamp(retakeAmount,0.f,1.f)*signedVariation;
    const auto matches=[&](int target){return retakeTarget==target||retakeTarget==7;};
    if(matches(1))c.toneColor=std::clamp(1.f+depth*.35f,.65f,1.35f);
    if(matches(2))c.dynamics=std::clamp(c.dynamics*(1.f+depth*.22f),0.f,1.f);
    if(matches(3))c.vibrato=std::clamp(c.vibrato+depth*.20f,0.f,1.f);
    if(matches(4)&&!authorityLock)c.pitchBend=std::clamp(c.pitchBend+depth*.0125f,0.f,1.f);
    if(matches(5))c.onsetDelayMs=std::max(0.f,2.f+depth*2.f);
    if(matches(6))c.attackCharacter=std::clamp(c.attackCharacter+depth*.22f,0.f,1.f);
    return c;
}
} // namespace Sonicraft::AIStrings
