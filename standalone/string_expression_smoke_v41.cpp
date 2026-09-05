#include "../src/string_expression_v41.h"
#include "../src/preview_engine.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace Sonicraft::AIStrings;
struct C {float dyn=.62f,vib=.5f,exp=.9f,leg=1.f,transition=.5f,tightness=.5f,attack=.38f;};
int main(){
    assert(stringPartForMidiChannel(0)==0 && stringPartForMidiChannel(4)==0 && stringPartForMidiChannel(6)==0);
    assert(stringPartForMidiChannel(1)==1 && stringPartForMidiChannel(7)==1 && stringPartForMidiChannel(9)==1);
    assert(stringPartForMidiChannel(2)==2 && stringPartForMidiChannel(10)==2 && stringPartForMidiChannel(12)==2);
    assert(stringPartForMidiChannel(3)==3 && stringPartForMidiChannel(13)==3 && stringPartForMidiChannel(15)==3);
    assert(stringVoiceIndexForMidiChannel(0)==0 && stringVoiceIndexForMidiChannel(4)==1 && stringVoiceIndexForMidiChannel(6)==3);
    const auto packed=packArticulationExpression(7,kExprAccent|kExprTenuto);
    assert(unpackBaseArticulation(packed)==7);
    assert(unpackExpressionStack(packed)==(kExprAccent|kExprTenuto));
    C c{};const auto m=applyStringExpressionModifiers(c,kExprAccent|kExprExpressive);
    assert(m.dyn>c.dyn && m.vib>c.vib && std::abs(m.attack-c.attack)>.01f);

    PreviewEngine e;e.setSampleRate(48000);
    PartControl a{},b{};a.articulation=7;a.dynamics=.45f;a.attackCharacter=.75f;b.articulation=0;b.dynamics=.85f;b.attackCharacter=.25f;
    e.noteOnVoice(0,0,72,.8f,a);
    e.noteOnVoice(0,4,76,.8f,b);
    float L[512]{},R[512]{};e.render(L,R,512);
    double energy=0;for(int i=0;i<512;++i)energy+=std::abs(L[i])+std::abs(R[i]);
    assert(energy>0.01);
    e.noteOffVoice(0,0,72);
    float L2[512]{},R2[512]{};e.render(L2,R2,512);
    double energy2=0;for(int i=0;i<512;++i)energy2+=std::abs(L2[i])+std::abs(R2[i]);
    assert(energy2>0.001); // the other lane is still alive
    std::cout<<"SONICRAFT v4.1 string expression/voice bus smoke OK\n";
    return 0;
}