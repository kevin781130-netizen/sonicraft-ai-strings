#include "../src/string_performance_critic_v48.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    CriticDimensionsV48 d{};
    d.bowReserve=50;d.transition=60;d.vibrato=70;d.dynamicsArc=80;d.gestureSpikes=90;d.ensembleAlignment=100;
    const auto s=weightedCriticScoreV48(d);
    assert(s>60.f && s<90.f);
    assert(repairBlendV48('B')>repairBlendV48('C') && repairBlendV48('C')>repairBlendV48('A'));
    assert(!structuralRepairCanAutoCommitV48());
    std::cout<<"SONICRAFT v4.8 performance critic native smoke OK score="<<s<<"\n";
    return 0;
}