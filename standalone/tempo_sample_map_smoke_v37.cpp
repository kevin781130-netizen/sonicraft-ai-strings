#include "../src/tempo_timeline.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    TempoTimelineCapture t;
    constexpr double sr=48000.0;
    t.observe(0.0,120.0,0);      // 0.5 sec per quarter
    t.observe(4.0,60.0,96000);   // after 2 sec, 1 sec per quarter
    std::int64_t s=0;
    assert(t.sampleAtBeat(2.0,sr,s)&&s==48000);
    assert(t.sampleAtBeat(4.0,sr,s)&&s==96000);
    assert(t.sampleAtBeat(6.0,sr,s)&&s==192000);
    assert(t.tempoAtBeat(2.0,68.0)==120.0);
    assert(t.tempoAtBeat(6.0,68.0)==60.0);
    std::cout<<"SONICRAFT v3.7 tempo beat/sample map smoke OK\n";
    return 0;
}
