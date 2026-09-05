#include "../src/conductor_intent_v53.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    assert(conductorIntentPassV53({90.f,1.0f,0}));
    assert(!conductorIntentPassV53({82.f,1.0f,0}));
    assert(!conductorIntentPassV53({92.f,1.8f,0}));
    assert(!conductorIntentPassV53({95.f,.5f,1}));
    assert(conductorAudioDropLimitV53()>.07f && conductorAudioDropLimitV53()<.08f);
    assert(sectionCharacterPriorV53('C',SectionCharacterV53::Climax)>
           sectionCharacterPriorV53('B',SectionCharacterV53::Climax));
    assert(sectionCharacterPriorV53('A',SectionCharacterV53::Resolution)>
           sectionCharacterPriorV53('C',SectionCharacterV53::Resolution));
    std::cout<<"SONICRAFT v5.3 conductor intent native smoke OK\n";
    return 0;
}