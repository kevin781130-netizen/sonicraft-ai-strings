#include "../src/global_performance_coherence_v52.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    assert(globalCoherencePassV52({90.f,.8f}));
    assert(!globalCoherencePassV52({79.f,.8f}));
    assert(!globalCoherencePassV52({95.f,1.8f}));
    assert(globalPairVerifyPassV52(.70f,.72f,.80f,.82f));
    assert(!globalPairVerifyPassV52(.68f,.72f,.80f,.82f));
    assert(!globalPairVerifyPassV52(.72f,.72f,.70f,.76f));
    assert(coherenceAudioDropLimitV52()>.07f && coherenceAudioDropLimitV52()<.08f);
    std::cout<<"SONICRAFT v5.2 global coherence native smoke OK\n";
    return 0;
}