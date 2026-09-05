#include "realtime_shell_core.h"
#include "low_latency_engine.h"
#include <chrono>
#include <iostream>
#include <string>
#include <vector>
using namespace Sonicraft::ProductShell;
using namespace Sonicraft::LowLatency;
int main(int argc,char**argv){
    std::string host="127.0.0.1",out="sonicraft_low_latency_sim.wav";int port=49337,blocks=8;
    for(int i=1;i<argc;++i){std::string a=argv[i];auto n=[&](){if(i+1>=argc)std::exit(2);return std::string(argv[++i]);};if(a=="--host")host=n();else if(a=="--port")port=std::stoi(n());else if(a=="--out")out=n();else if(a=="--blocks")blocks=std::stoi(n());}
    const uint32_t sr=48000;MidiTimestampCalibrator mt;mt.reset(sr,1000,0);if(mt.sampleFor(10)!=1480){std::cerr<<"midi timestamp calibration failed\n";return 10;}RendererClient c(host,port);if(!c.ping(sr)){std::cerr<<"service offline\n";return 3;}
    Timeline tl;Policy p;p.mode=1;p.multiOut=true;p.lookahead=.04f;MixerState mix;mix.master=.78f;mix.feed[4]=.22f;
    AdaptiveQuantumController aq;GlitchGuard gg(48);std::vector<float> all;uint64_t req=250001;int64_t cursor=0;double lastMs=0;bool deadlineMiss=false;
    tl.pushMidiShort(0x90,69,104,0,p.tempo);
    // Sustain pedal must hold the note after key release, then release exactly on CC64-up.
    tl.pushMidiShort(0xB0,64,127,1200,p.tempo);tl.pushMidiShort(0x80,69,0,2400,p.tempo);
    if(!tl.anyActiveNotes()){std::cerr<<"sustain semantics failed\n";return 8;}
    tl.pushMidiShort(0xB0,64,0,5200,p.tempo);
    std::vector<int> quanta;
    for(int b=0;b<std::max(1,blocks);++b){
        bool attack=(b==0);auto qd=aq.choose(attack,lastMs,deadlineMiss,b>0?1:0);quanta.push_back(qd.quantumMs);int64_t q=int64_t(sr)*qd.quantumMs/1000;int64_t start=cursor,end=start+q;auto ev=tl.contextFor(start,end,int64_t(sr)*4);if(ev.empty()){
            // Preserve a stable control context for tail windows after the pedal release.
            auto snap=tl.controlsSnapshot();TimelineEvent e{};e.sample=start;e.type=4;e.part=0;e.tempo=p.tempo;e.controls=snap[0];ev.push_back(e);
        }
        RenderAudio a;auto t0=std::chrono::steady_clock::now();if(!c.render(ev,start,end,sr,p,req++,a)){std::cerr<<"render failed block="<<b<<"\n";return 4;}lastMs=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t0).count();deadlineMiss=lastMs>qd.quantumMs;auto y=mixToStereo(a,mix);gg.processStereo(y,b==blocks-1);all.insert(all.end(),y.begin(),y.end());cursor=end;if(a.channels!=34)return 5;
    }
    if(quanta.empty()||quanta.front()!=40){std::cerr<<"attack quantum was not 40ms\n";return 9;}
    if(!writePcm16Wav(out,all,sr))return 6;
    std::cout<<"v2.5 LOW LATENCY SIM PASS first_quantum_ms="<<quanta.front()<<" blocks="<<quanta.size()<<" last_request_ms="<<lastMs<<" out="<<out<<"\n";return 0;
}
