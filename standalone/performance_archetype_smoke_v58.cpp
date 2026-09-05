#include "../src/performance_archetype_v58.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    assert(archetypeEvidenceAllowedV58({.75f,1.f,2.f}));
    assert(!archetypeEvidenceAllowedV58({.30f,1.f,2.f}));
    assert(!archetypeEvidenceAllowedV58({.75f,.25f,2.f}));
    assert(!archetypeOnlyTop1AllowedV58());
    assert(archetypeNoLocalConfidenceCapV58()<.72f);
    assert(archetypeEvidenceScaleV58()<.5f);
    std::cout<<"SONICRAFT v5.8 performance archetype native smoke OK\n";
    return 0;
}