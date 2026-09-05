#include "../src/string_transition_v46.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    assert(std::abs(previewGesturePitchBendV46(1.f,1.f)-.625f)<1e-6f);
    assert(std::abs(previewGesturePitchBendV46(0.f,1.f)-.375f)<1e-6f);
    assert(std::abs(previewGesturePitchBendV46(.8f,0.f)-.8f)<1e-6f);
    const auto a=transitionContinuityRiskV46(2,2,0,true);
    const auto b=transitionContinuityRiskV46(12,10,2,false);
    assert(a<b && b>.5f);
    std::cout<<"SONICRAFT v4.6 transition helper smoke OK\n";
    return 0;
}