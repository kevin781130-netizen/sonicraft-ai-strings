#include "low_latency_engine.h"
#include <cmath>

namespace Sonicraft::LowLatency {

void AdaptiveQuantumController::reset(){currentMs_=80;stableFast_=0;misses_=0;}
QuantumDecision AdaptiveQuantumController::choose(bool freshAttack,double previousRenderMs,bool deadlineMiss,int queuedBlocks){
    // Attack gets the smallest practical neural slice.  Sustains expand only when the renderer
    // needs more slack.  This is scheduling policy only; it never changes authored MIDI.
    if(freshAttack){currentMs_=40;stableFast_=0;return {currentMs_,"fresh-attack"};}
    if(deadlineMiss){misses_++;stableFast_=0;currentMs_=std::min(160,std::max(80,currentMs_*2));return {currentMs_,"deadline-recovery"};}
    const double rtf=previousRenderMs/std::max(1,currentMs_);
    if(rtf<.28 && queuedBlocks>=1){stableFast_++;if(stableFast_>=3)currentMs_=std::max(40,currentMs_/2);}
    else if(rtf>.72 || queuedBlocks==0){stableFast_=0;currentMs_=std::min(160,std::max(80,currentMs_*2));}
    else stableFast_=0;
    return {currentMs_, currentMs_<=40?"low-latency":(currentMs_<=80?"balanced":"stability")};
}

void MidiTimestampCalibrator::reset(uint32_t sr,int64_t origin,uint32_t midiOrigin){sampleRate_=std::max<uint32_t>(8000,sr);timelineOrigin_=origin;midiOriginMs_=midiOrigin;}
int64_t MidiTimestampCalibrator::sampleFor(uint32_t ms)const{
    // Unsigned subtraction intentionally handles WinMM's 32-bit wraparound.
    uint32_t delta=ms-midiOriginMs_;
    return timelineOrigin_+int64_t((uint64_t(delta)*sampleRate_+500)/1000);
}

void GlitchGuard::reset(){haveLast_=false;lastL_=lastR_=0.f;}
void GlitchGuard::processStereo(std::vector<float>& x,bool hardRelease){
    if(x.size()<2)return;const size_t frames=x.size()/2;const size_t n=std::min<size_t>(frames,size_t(rampFrames_));
    if(haveLast_){for(size_t i=0;i<n;++i){float a=float(i+1)/float(n+1);x[2*i]=lastL_*(1.f-a)+x[2*i]*a;x[2*i+1]=lastR_*(1.f-a)+x[2*i+1]*a;}}
    if(hardRelease){for(size_t i=0;i<n;++i){size_t f=frames-1-i;float a=float(i)/float(std::max<size_t>(1,n-1));x[2*f]*=a;x[2*f+1]*=a;}}
    lastL_=x[x.size()-2];lastR_=x[x.size()-1];haveLast_=true;
}

} // namespace Sonicraft::LowLatency
