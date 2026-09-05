#include "../src/candidate_utility_predictor_v55.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    assert(highConfidenceTop1V55({.80f,.18f,5.f}));
    assert(!highConfidenceTop1V55({.60f,.18f,5.f}));
    assert(mediumConfidenceTop2V55({.55f,.05f,2.f}));
    assert(candidateUtilityEscalateV55(.01f,true,.9f,.9f));
    assert(candidateUtilityEscalateV55(.20f,false,.9f,.9f));
    assert(!candidateUtilityEscalateV55(.20f,true,.9f,.9f));
    assert(!skippedCandidateMayLearnV55());
    assert(originalDAlwaysRenderedV55());
    std::cout<<"SONICRAFT v5.5 Candidate Utility Predictor native smoke OK\n";
    return 0;
}
