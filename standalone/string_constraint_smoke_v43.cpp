#include "../src/string_constraint_v43.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    auto a=assessStringTransitionV43(2,0,.5f,false);
    auto b=assessStringTransitionV43(11,2,0.f,true);
    assert(a.risk<b.risk && b.highRisk);
    assert(doubleStopFrameFeasibleV43(1,7,2,2,7));
    assert(!doubleStopFrameFeasibleV43(1,3,1,7,7));
    assert(!doubleStopFrameFeasibleV43(1,2,2,13,7));
    assert(bowBudgetNeedsChangeV43(4.7f,1.0f,.8f,5.0f,true));
    assert(!bowBudgetNeedsChangeV43(4.7f,1.0f,.8f,5.0f,false));
    std::cout<<"SONICRAFT v4.3 string constraint native smoke OK\n";
    return 0;
}