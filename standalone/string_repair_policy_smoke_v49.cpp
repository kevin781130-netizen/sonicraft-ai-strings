#include "../src/string_repair_policy_v49.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    assert(!repairLearningGateV49(.01f,.9f,.9f,false));
    assert(!repairLearningGateV49(.08f,.2f,.9f,false));
    assert(!repairLearningGateV49(.08f,.9f,.9f,true));
    assert(repairLearningGateV49(.08f,.9f,.9f,false));
    RepairPolicyV49 p{};
    auto b=updateRepairPolicyV49(p,'B',.10f);
    assert(b.smoothing>p.smoothing && b.transition>p.transition && b.expressiveApex<p.expressiveApex);
    auto d=updateRepairPolicyV49(p,'D',.10f);
    assert(d.smoothing<p.smoothing && d.bowRelief<p.bowRelief);
    std::cout<<"SONICRAFT v4.9 repair policy native smoke OK\n";
    return 0;
}