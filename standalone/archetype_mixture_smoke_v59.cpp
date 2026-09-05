#include "../src/archetype_mixture_v59.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    assert(mixtureComponentAllowedV59({.8f,.4f,1.f}));
    assert(!mixtureComponentAllowedV59({.3f,.4f,1.f}));
    assert(!mixtureComponentAllowedV59({.8f,.04f,1.f}));
    assert(!mixtureComponentAllowedV59({.8f,.4f,.25f}));
    assert(!mixtureOnlyTop1AllowedV59());
    assert(maxMixtureComponentsV59()==3);
    assert(mixtureNoLocalConfidenceCapV59()<.72f);
    std::cout<<"SONICRAFT v5.9 archetype mixture native smoke OK\n";
    return 0;
}