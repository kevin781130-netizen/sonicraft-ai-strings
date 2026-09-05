#include "../src/string_shadow_auto_loop_v50.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    assert(shadowLoopGateV50(.01f,.9f,.9f,false,1,6)==ShadowLoopStopV50::LowMargin);
    assert(shadowLoopGateV50(.08f,.2f,.9f,false,1,6)==ShadowLoopStopV50::SafetyFloor);
    assert(shadowLoopGateV50(.08f,.9f,.2f,false,1,6)==ShadowLoopStopV50::LowOverall);
    assert(shadowLoopGateV50(.08f,.9f,.9f,true,1,6)==ShadowLoopStopV50::StalePolicy);
    assert(shadowLoopGateV50(.08f,.9f,.9f,false,6,6)==ShadowLoopStopV50::RoundCap);
    assert(shadowLoopGateV50(.08f,.9f,.9f,false,1,6)==ShadowLoopStopV50::Continue);
    assert(shadowLoopMayLearnV50(ShadowLoopStopV50::RoundCap));
    assert(!shadowLoopMayLearnV50(ShadowLoopStopV50::LowMargin));
    assert(shadowLoopMaxRoundsV50()==6);
    std::cout<<"SONICRAFT v5.0 Shadow auto-loop gate native smoke OK\n";
    return 0;
}
