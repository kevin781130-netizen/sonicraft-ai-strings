#pragma once
#include <algorithm>
#include <cmath>

namespace Sonicraft::AIStrings {

inline float previewGesturePitchBendV46(float rawNormalized,float gestureAmount) noexcept {
    // CC39 is +/-50 cents. PreviewEngine's historical pitch-bend convention is +/-2 semitones,
    // so shrink only the Preview copy by 4x. Shadow/HQ retains the raw authored value.
    if(gestureAmount<=.0001f)return std::clamp(rawNormalized,0.f,1.f);
    return std::clamp(.5f+(std::clamp(rawNormalized,0.f,1.f)-.5f)*.25f,0.f,1.f);
}

inline float transitionContinuityRiskV46(int intervalSemitones,int shiftSemitones,
                                         int stringCrossings,bool sameBow) noexcept {
    float risk=std::abs(float(intervalSemitones))*.025f+std::abs(float(shiftSemitones))*.035f+
               std::abs(float(stringCrossings))*.08f+(sameBow?0.f:.10f);
    return std::clamp(risk,0.f,1.f);
}

} // namespace Sonicraft::AIStrings
