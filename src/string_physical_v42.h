#pragma once
#include <algorithm>
#include <cstdint>

namespace Sonicraft::AIStrings {

enum StringPhysicalOpcode : std::uint8_t {
    kPhysString=112,kPhysPosition=113,kPhysBowDirection=114,kPhysBowChange=115,
    kPhysBowPressure=116,kPhysContactPoint=117,kPhysPortamento=118,kPhysDesk=119,
};

struct StringPhysicalStateV42 {
    float stringIndex=.5f;
    float position=0.f;
    float bowDirection=0.f;
    float bowChange=1.f;
    float bowPressure=.5f;
    float contactPoint=.5f;
    float portamento=0.f;
    float desk=0.f;
};

template<class C>
inline C applyStringPhysicalResidualsV42(C c,const StringPhysicalStateV42& p,std::uint8_t mask=0xFF) noexcept {
    if(mask&0x02){c.vib=std::clamp(c.vib+(p.position-.25f)*.08f,0.f,1.f);c.attack=std::clamp(c.attack-p.position*.055f,0.f,1.f);}
    if(mask&0x01){c.attack=std::clamp(c.attack+(p.stringIndex-.5f)*.035f,0.f,1.f);c.transition=std::clamp(c.transition+(p.stringIndex-.5f)*.018f,0.f,1.f);}
    if(mask&0x04)c.attack=std::clamp(c.attack+(0.5f-p.bowDirection)*.07f,0.f,1.f);
    if(mask&0x10){c.dyn=std::clamp(c.dyn+(p.bowPressure-.5f)*.10f,0.f,1.f);c.attack=std::clamp(c.attack+(p.bowPressure-.5f)*.15f,0.f,1.f);c.tightness=std::clamp(c.tightness+(p.bowPressure-.5f)*.10f,0.f,1.f);}
    if(mask&0x20){c.attack=std::clamp(c.attack+(p.contactPoint-.5f)*.12f,0.f,1.f);c.tightness=std::clamp(c.tightness+(p.contactPoint-.5f)*.11f,0.f,1.f);c.exp=std::clamp(c.exp-(p.contactPoint-.5f)*.035f,0.f,1.f);c.vib=std::clamp(c.vib-(p.contactPoint-.5f)*.045f,0.f,1.f);}
    if(mask&0x40){c.leg=std::max(c.leg,p.portamento*.92f);c.transition=std::clamp(c.transition-p.portamento*.22f,0.f,1.f);c.bend=std::clamp(c.bend+p.portamento*.012f,0.f,1.f);}
    if((mask&0x02)&&p.position<.01f)c.vib=std::min(c.vib,.08f);
    if(mask&0x80){const float d=(p.desk*2.f-1.f)*.012f;c.dyn=std::clamp(c.dyn+d,0.f,1.f);c.attack=std::clamp(c.attack-d*.7f,0.f,1.f);}
    return c;
}

} // namespace Sonicraft::AIStrings
