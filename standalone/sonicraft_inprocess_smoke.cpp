#include "inprocess_neural_engine.h"
#include <algorithm>
#include <cmath>
#include <iostream>
using namespace Sonicraft::ProductShell;
using namespace Sonicraft::InProcess;
int main(){
    std::vector<TimelineEvent> ev;
    Controls c{};c.dyn=.68f;c.vib=.42f;c.exp=.91f;c.room=.2f;
    auto push=[&](int64_t s,int typ,int part,int note,float vel){TimelineEvent e{};e.sample=s;e.type=uint8_t(typ);e.part=uint8_t(part);e.note=uint8_t(note);e.velocity=vel;e.tempo=72;e.controls=c;ev.push_back(e);};
    // Three overlapping Vln I notes + quartet context.
    push(0,1,0,60,.82f);push(480,1,0,64,.76f);push(960,1,0,67,.72f);push(0,1,1,55,.7f);push(0,1,2,48,.7f);push(0,1,3,36,.7f);
    push(6000,2,0,60,0);push(6500,2,0,64,0);push(7000,2,0,67,0);push(7600,2,1,55,0);push(7600,2,2,48,0);push(7600,2,3,36,0);
    auto lanes=allocatePolyphonicLanes(ev,0,16);if(lanes.size()!=3){std::cerr<<"poly lanes="<<lanes.size()<<"\n";return 2;}
    Policy p{};p.multiOut=true;p.polyphony=true;p.assist=1;p.smartDynamics=false;p.smartArticulation=false;p.mode=1;p.tempo=72;
    NativeControlBuilder cb;auto cc=cb.build(ev,lanes[0],0,0,9600,48000,p,"smoke");if(cc.frames!=20||cc.raw.size()!=size_t(cc.frames*kRawControls)||cc.frontierContext.size()!=size_t(cc.frames*kFrontierContext)){std::cerr<<"control shape\n";return 3;}
    if(*std::max_element(cc.gate.begin(),cc.gate.end())<.9f){std::cerr<<"gate\n";return 4;}
    auto sess=std::make_shared<DeterministicMockSession>();EngineConfig cfg;cfg.stepsAuto=2;InProcessEngine eng(sess,cfg);EngineRender out;if(!eng.render(ev,0,9600,p,out)){std::cerr<<"render failed\n";return 5;}
    if(out.channels!=34||out.frames!=9600||out.interleaved.size()!=size_t(9600*34)||out.voicesRendered<6||out.neuralCalls<12){std::cerr<<"render shape/voices/calls "<<out.channels<<" "<<out.frames<<" "<<out.voicesRendered<<" "<<out.neuralCalls<<"\n";return 6;}
    float peak=0;for(float x:out.interleaved)peak=std::max(peak,std::abs(x));if(!(peak>0&&peak<.99f)){std::cerr<<"peak="<<peak<<"\n";return 7;}
    // Strict MIDI authority default: smart features off must keep dynamics anchor nearly unchanged.
    auto base=cb.build(ev,lanes[0],0,0,9600,48000,p,"smoke");p.smartDynamics=true;auto smart=cb.build(ev,lanes[0],0,0,9600,48000,p,"smoke");bool changed=false;for(int i=0;i<base.frames;++i)if(std::abs(base.raw[size_t(i*kRawControls+4)]-smart.raw[size_t(i*kRawControls+4)])>1e-5f){changed=true;break;}if(!changed){std::cerr<<"smart dynamics inactive\n";return 8;}
    std::cout<<"v2.8 C++ INPROCESS ENGINE PASS voices="<<out.voicesRendered<<" calls="<<out.neuralCalls<<" frames="<<out.frames<<" channels="<<out.channels<<" peak="<<peak<<"\n";
    return 0;
}
