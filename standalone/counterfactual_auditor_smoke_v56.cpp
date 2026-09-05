#include "../src/counterfactual_auditor_v56.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    CounterfactualAuditStateV56 s{};
    assert(auditIntervalV56(s)==12);
    assert(falsePruneV56(.90f,.96f,.91f,true));
    assert(!falsePruneV56(.90f,.915f,.91f,true));
    s.audits=4;s.falsePrunes=1;
    assert(disableZeroRenderV56(s));
    assert(auditIntervalV56(s)==4);
    s.disabled=true;s.cleanStreak=4;
    assert(auditIntervalV56(s)==1);
    assert(recoverZeroRenderV56(s));
    std::cout<<"SONICRAFT v5.6 counterfactual auditor native smoke OK\n";
    return 0;
}