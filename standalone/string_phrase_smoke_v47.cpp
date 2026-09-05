#include "../src/string_phrase_v47.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    const auto a=phraseEnergyArcV47(0.f);
    const auto m=phraseEnergyArcV47(.62f);
    const auto e=phraseEnergyArcV47(1.f);
    assert(m>a && m>e);
    assert(phraseVibratoRateHzV47(1.f)>phraseVibratoRateHzV47(0.f));
    auto r=phraseBowReserveV47(1.f,2.f,.6f,false);
    assert(r<1.f && r>0.f);
    auto reset=phraseBowReserveV47(.1f,.5f,.4f,true);
    assert(reset>.8f);
    std::cout<<"SONICRAFT v4.7 phrase long-line native smoke OK\n";
    return 0;
}