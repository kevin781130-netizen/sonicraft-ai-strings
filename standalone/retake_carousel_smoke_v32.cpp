#include "../src/retake_carousel_v32.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    assert(takeIndexFromNormalized(0.f)==0);
    assert(takeIndexFromNormalized(1.f)==3);
    const float base=.37123f;
    const float a=deriveTakeNonce(base,0), b=deriveTakeNonce(base,1), c=deriveTakeNonce(base,2), d=deriveTakeNonce(base,3);
    assert(std::abs(a-base)<1e-7f);
    assert(b>=0.f&&b<=1.f&&c>=0.f&&c<=1.f&&d>=0.f&&d<=1.f);
    assert(std::abs(b-c)>1e-6f && std::abs(c-d)>1e-6f && std::abs(b-d)>1e-6f);
    assert(deriveTakeNonce(base,2)==c); // deterministic

    HostCycleWindow w{true,8.0,12.0};
    assert(detectCycleWrap(11.9,8.05,w,w));
    assert(!detectCycleWrap(9.0,8.8,w,w));
    assert(!detectCycleWrap(10.0,10.1,w,w));

    RetakeCarouselTracker t;
    assert(t.update(kTakeCarouselAutoLoop,1,false,false,true,8.0,w)==1); // stopped resets to selected B
    assert(t.update(kTakeCarouselAutoLoop,1,false,true,true,8.0,w)==1);  // fresh play starts B
    assert(t.update(kTakeCarouselAutoLoop,1,false,true,true,11.9,w)==1);
    assert(t.update(kTakeCarouselAutoLoop,1,false,true,true,8.05,w)==2); // wrap -> C
    assert(t.update(kTakeCarouselAutoLoop,1,true,true,true,11.9,w)==2);
    assert(t.update(kTakeCarouselAutoLoop,1,true,true,true,8.05,w)==2);  // frozen
    assert(t.update(kTakeCarouselManual,3,false,true,true,9.0,w)==3);    // manual D
    assert(t.update(kTakeCarouselAutoLoop,0,false,false,true,9.0,w)==0); // stop primes A
    assert(t.update(kTakeCarouselAutoLoop,0,false,true,true,8.0,w)==0);

    const float nOutside=resolveCarouselNonce(kTakeCarouselManual,true,false,base,3,2);
    assert(std::abs(nOutside-base)<1e-7f);
    const float nInside=resolveCarouselNonce(kTakeCarouselManual,true,true,base,3,2);
    assert(std::abs(nInside-d)<1e-7f);
    const float nNoRetake=resolveCarouselNonce(kTakeCarouselAutoLoop,false,true,base,0,2);
    assert(std::abs(nNoRetake-base)<1e-7f);
    std::cout << "SONICRAFT v3.2 deterministic retake carousel smoke OK\n";
    return 0;
}
