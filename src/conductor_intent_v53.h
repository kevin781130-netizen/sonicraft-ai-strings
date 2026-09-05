#pragma once
#include <algorithm>

namespace Sonicraft::AIStrings {

enum class SectionCharacterV53 {
    Intro, Build, Sustain, Climax, Release, Resolution
};

struct ConductorIntentGateV53 {
    float score=100.f;
    float maxSectionExcess=0.f;
    int hardViolations=0;
};

inline bool conductorIntentPassV53(ConductorIntentGateV53 g) noexcept {
    return g.score>=84.f && g.maxSectionExcess<=1.55f && g.hardViolations==0;
}

inline float conductorAudioDropLimitV53() noexcept { return .075f; }
inline float mergedVsDOverallToleranceV53() noexcept { return -.025f; }
inline float mergedVsDSafetyToleranceV53() noexcept { return -.04f; }

inline float sectionCharacterPriorV53(char slot,SectionCharacterV53 c) noexcept {
    if(c==SectionCharacterV53::Climax)
        return slot=='C' ? .008f : (slot=='B' ? .003f : (slot=='A' ? -.002f : 0.f));
    if(c==SectionCharacterV53::Build)
        return slot=='C' ? .005f : (slot=='B' ? .004f : 0.f);
    if(c==SectionCharacterV53::Intro || c==SectionCharacterV53::Release || c==SectionCharacterV53::Resolution)
        return slot=='A' ? .005f : (slot=='D' ? .003f : (slot=='B' ? .001f : -.003f));
    return slot=='B' ? .004f : ((slot=='A'||slot=='C') ? .001f : 0.f);
}

} // namespace Sonicraft::AIStrings
