#include "../src/string_ensemble_v44.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
struct C {float attack=.38f,tightness=.50f,transition=.50f;};
int main(){
    C c{};
    StringEnsembleStateV44 e{};
    e.attackOffset=.75f;e.phraseBreath=.5f;
    auto x=applyStringEnsemblePreviewResidualsV44(c,e,0x03);
    assert(x.attack<c.attack);
    assert(x.tightness!=c.tightness);
    assert(x.transition>c.transition);
    auto legacy=applyStringEnsemblePreviewResidualsV44(c,e,0x00);
    assert(legacy.attack==c.attack && legacy.tightness==c.tightness && legacy.transition==c.transition);
    static_assert(kEnsembleAttackOffset==120);
    static_assert(kEnsemblePhraseBreath==121);
    std::cout<<"SONICRAFT v4.4 string ensemble preview smoke OK\n";
    return 0;
}