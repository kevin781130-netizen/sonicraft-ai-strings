#include "../src/host_cycle_scope_v31.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    HostCycleWindow w{true,8.0,12.0};
    assert(!hostScopeInside(7.999,w)); assert(hostScopeInside(8.0,w)); assert(hostScopeInside(11.999,w)); assert(!hostScopeInside(12.0,w));
    auto outside=resolveHostScope(kHostScopeBoth,false,.2f,5.f/7.f,.75f,.4f,1.f,.18f,1.f,.44f);
    assert(outside.retakeTarget==0.f && outside.retakeAmount==0.f); assert(std::abs(outside.performanceStyle-.2f)<1e-6f); assert(std::abs(outside.ensembleLooseness-.18f)<1e-6f);
    auto inside=resolveHostScope(kHostScopeBoth,true,.2f,5.f/7.f,.75f,.4f,0.f,.18f,1.f,.44f);
    assert(std::abs(inside.retakeTarget-5.f/7.f)<1e-6f); assert(std::abs(inside.retakeAmount-.75f)<1e-6f); assert(std::abs(inside.performanceStyle-1.f)<1e-6f); assert(inside.phraseDirector==1.f); assert(std::abs(inside.ensembleLooseness-.44f)<1e-6f);
    // 120 BPM = 0.5 sec / quarter; at 48 kHz one quarter = 24000 samples.
    assert(boundarySampleOffset(8.0,8.5,120.0,48000.0,24000)==12000);
    assert(boundarySampleOffset(8.0,9.0,120.0,48000.0,24000)==-1); // block end is not an internal boundary
    std::cout << "SONICRAFT v3.1 host cycle scope smoke OK\n";
    return 0;
}
