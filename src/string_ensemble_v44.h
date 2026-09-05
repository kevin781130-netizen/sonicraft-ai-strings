#pragma once
#include <algorithm>
#include <cstdint>

namespace Sonicraft::AIStrings {

enum StringEnsembleOpcodeV44 : std::uint8_t {
    kEnsembleAttackOffset=120,
    kEnsemblePhraseBreath=121,
};

struct StringEnsembleStateV44 {
    float attackOffset=.5f; // .5 = zero, 0/1 = -/+ max offset
    float phraseBreath=0.f;
};

template<class C>
inline C applyStringEnsemblePreviewResidualsV44(C c,const StringEnsembleStateV44& e,std::uint8_t mask=0x03) noexcept {
    // Preview cannot schedule sub-block latency safely, so it approximates the authored HQ
    // timing intent through onset/release character. HQ renderer applies the actual ms offsets.
    if(mask&0x01){
        const float signedOffset=(std::clamp(e.attackOffset,0.f,1.f)-.5f)*2.f;
        c.attack=std::clamp(c.attack-signedOffset*.055f,0.f,1.f);
        c.tightness=std::clamp(c.tightness-signedOffset*.035f,0.f,1.f);
    }
    if(mask&0x02){
        const float b=std::clamp(e.phraseBreath,0.f,1.f);
        c.transition=std::clamp(c.transition+b*.05f,0.f,1.f);
        c.tightness=std::clamp(c.tightness+b*.04f,0.f,1.f);
    }
    return c;
}

} // namespace Sonicraft::AIStrings
