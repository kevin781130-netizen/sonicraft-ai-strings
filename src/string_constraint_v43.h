#pragma once
#include <algorithm>
#include <cmath>

namespace Sonicraft::AIStrings {

struct StringTransitionAssessmentV43 {
    float risk=0.f;
    bool highRisk=false;
};

inline StringTransitionAssessmentV43 assessStringTransitionV43(
    int shiftSemitones,int stringCrossings,float gapBeats,bool connected) noexcept {
    const float timeRelief=std::min(1.f,std::max(0.f,gapBeats)*1.8f);
    float risk=std::abs(float(shiftSemitones))/12.f+std::abs(float(stringCrossings))*.18f-timeRelief*.35f;
    if(connected)risk=std::max(risk,std::abs(float(shiftSemitones))/10.f+std::abs(float(stringCrossings))*.14f);
    risk=std::clamp(risk,0.f,1.f);
    return {risk,risk>=.72f};
}

inline bool doubleStopFrameFeasibleV43(
    int stringA,int fingerA,int stringB,int fingerB,int maxStoppedSpan=7) noexcept {
    if(std::abs(stringA-stringB)!=1)return false;
    if(fingerA<0||fingerB<0)return false;
    if(fingerA==0||fingerB==0)return true;
    return std::abs(fingerA-fingerB)<=std::max(0,maxStoppedSpan);
}

inline bool bowBudgetNeedsChangeV43(
    float budgetBeats,float noteBeats,float pressure,float limitBeats,bool connected) noexcept {
    if(!connected)return false;
    const float consumption=std::max(0.f,noteBeats)*(.52f+std::clamp(pressure,0.f,1.f)*.62f);
    return budgetBeats+consumption>std::max(.25f,limitBeats);
}

} // namespace Sonicraft::AIStrings
