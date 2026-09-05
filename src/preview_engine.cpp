#include "preview_engine.h"
#include <algorithm>
namespace Sonicraft::AIStrings {
Voice* PreviewEngine::allocateVoice(){for(auto& v:voices)if(!v.active)return &v;return &voices.front();}
float PreviewEngine::panForPart(int p)const{static constexpr float stage[4]={-.48f,-.16f,.14f,.40f};const float o=(ctl[p].pan-.5f)*.55f;return std::max(-.95f,std::min(.95f,stage[p]+o));}
float PreviewEngine::toneForPart(int p)const{static constexpr float tone[4]={1.f,.96f,.88f,.76f};return tone[p];}
void PreviewEngine::setPartSustain(int p,bool v){if(!validPart(p))return;const bool was=ctl[p].sustain;ctl[p].sustain=v;if(was&&!v)for(auto& voice:voices)if(voice.active&&voice.channel==p&&voice.keyReleased){voice.releasing=true;voice.target=0.;}}
void PreviewEngine::noteOn(int channel,int note,float velocity){if(!validPart(channel))return;auto* v=allocateVoice();*v=Voice{};v->active=true;v->note=note;v->channel=channel;v->lane=-1;v->velocity=std::max(.02f,velocity);v->articulation=ctl[channel].articulation;const double cents=((channel*17+note*7)%11-5)*humanize*.55;v->baseFreq=midiToHz(note)*std::pow(2.,cents/1200.);v->target=1.;}
void PreviewEngine::noteOff(int channel,int note){if(!validPart(channel))return;for(auto& v:voices)if(v.active&&v.channel==channel&&v.lane<0&&v.note==note){v.keyReleased=true;if(!ctl[channel].sustain){v.releasing=true;v.target=0.;}}}
void PreviewEngine::noteOnVoice(int part,int lane,int note,float velocity,const PartControl& control){if(!validPart(part)||lane<0||lane>=16)return;
    double carryVib=0.0,carryJitter=0.0,carryEnv=0.0;bool haveCarry=false;
    if(control.continuousGesture){
        for(const auto& old:voices)if(old.active&&old.channel==part&&old.lane==lane){
            carryVib=old.vibPhase;carryJitter=old.vibJitterPhase;carryEnv=old.env;haveCarry=true;break;
        }
    }
    auto* v=allocateVoice();*v=Voice{};v->active=true;v->note=note;v->channel=part;v->lane=lane;v->localControl=control;
    v->velocity=std::max(.02f,velocity);v->articulation=control.articulation;
    const double cents=((part*17+note*7+lane*3)%11-5)*humanize*.55;v->baseFreq=midiToHz(note)*std::pow(2.,cents/1200.);
    if(haveCarry){v->vibPhase=carryVib;v->vibJitterPhase=carryJitter;v->env=std::min(.92,carryEnv*.78);v->ageSeconds=.18;}
    v->target=1.;
}
void PreviewEngine::noteOffVoice(int part,int lane,int note){if(!validPart(part)||lane<0||lane>=16)return;for(auto& v:voices)if(v.active&&v.channel==part&&v.lane==lane&&v.note==note){v.keyReleased=true;if(!v.localControl.sustain){v.releasing=true;v.target=0.;}}}
void PreviewEngine::updateVoiceLaneControl(int lane,const PartControl& control){if(lane<0||lane>=16)return;for(auto& v:voices)if(v.active&&v.lane==lane){v.localControl=control;v.articulation=control.articulation;}}
void PreviewEngine::allNotesOff(){for(auto& v:voices){v.releasing=true;v.target=0.;}}

double PreviewEngine::vibratoDepthCents(float cc3)const{
    const double x=clamp01(cc3)*127.0; static constexpr double xp[5]={0,32,64,96,127};static constexpr double yp[5]={0,12,28,48,72};
    for(int i=0;i<4;++i){
        if(x<=xp[i+1]){const double t=(x-xp[i])/(xp[i+1]-xp[i]);return yp[i]+t*(yp[i+1]-yp[i]);}
    }
    return yp[4];
}
double PreviewEngine::vibratoRateHz(int part,int note,float cc3,const PartControl& c)const{
    const double inst=(part<2)?.12:(part==2?-.05:-.22);const double reg=.10*std::max(-1.,std::min(1.,(note-64.)/24.));
    const double tempo=.12*std::max(-1.,std::min(1.,(tempoBpm-72.)/36.));
    double speed=0.; if(c.speedProfile>=.17f&&c.speedProfile<.50f)speed=-.62;else if(c.speedProfile>=.84f)speed=.68;
    return std::max(4.0,std::min(7.2,5.15+.35*cc3+inst+reg+tempo+speed));
}
double PreviewEngine::transitionSeconds(int articulation,const PartControl& c)const{
    // v0.7 mirrors the HQ renderer's beat-domain timing policy.  The VST LIVE engine still
    // uses conservative priors; the CUDA renderer replaces them with learned calibration
    // from rights-cleared transitions when available.
    const double spb=60.0/std::max(24.0,std::min(240.0,tempoBpm));
    double slow=.095,normal=.065,fast=.042,lo=.012,hi=.150;
    if(articulation==(int)Articulation::Portamento){slow=.390;normal=.250;fast=.145;lo=.045;hi=.430;}
    else if(articulation==(int)Articulation::Legato){slow=.145;normal=.095;fast=.060;lo=.018;hi=.190;}
    double beats=normal;
    if(c.speedProfile<.17f){
        const double x=std::max(0.0,std::min(1.0,double(c.transitionSpeed)));
        if(x<=.5)beats=slow+(normal-slow)*(x/.5);else beats=normal+(fast-normal)*((x-.5)/.5);
    }else{
        if(c.speedProfile<.50f)beats=slow;else if(c.speedProfile<.84f)beats=normal;else beats=fast;
        beats*=1.12-.24*std::max(0.0,std::min(1.0,double(c.transitionSpeed)));
    }
    return std::max(lo,std::min(hi,beats*spb));
}

void PreviewEngine::render(float* left,float* right,int32_t n){if(!left||!right)return;const double twoPi=6.2831853071795864769;
    for(int i=0;i<n;++i){float L=0,R=0;for(auto& v:voices){if(!v.active)continue;const int p=v.channel;const auto& c=(v.lane>=0?v.localControl:ctl[p]);const int a=v.articulation;v.ageSeconds+=1.0/sampleRate;
        const bool shortArt=(a==(int)Articulation::Staccato||a==(int)Articulation::Spiccato||a==(int)Articulation::Pizzicato||a==(int)Articulation::Marcato);
        const double attackScale=1.45-.90*c.attackCharacter;double atk=.020*attackScale,rel=.22;
        const double trans=transitionSeconds(a,c);if(a==(int)Articulation::Legato)atk=c.legato?std::max(.0025,trans*.055):.015;else if(a==(int)Articulation::Portamento)atk=std::max(.004,trans*.055);else if(a==(int)Articulation::ExpressiveLong)atk=.045;else if(a==(int)Articulation::Marcato)atk=.003;else if(a==(int)Articulation::Staccato)atk=.0035;else if(a==(int)Articulation::Spiccato)atk=.0018;else if(a==(int)Articulation::Pizzicato)atk=.0015;else if(a==(int)Articulation::Flautando)atk=.060;
        if(shortArt){const double tight=1.55-1.10*c.shortTightness;rel=((a==(int)Articulation::Pizzicato)?.10:.055)*tight;}
        const double coef=1.-std::exp(-1./(sampleRate*(v.releasing?rel:atk)));v.env+=(v.target-v.env)*coef;if(v.releasing&&v.env<1e-4){v.active=false;continue;}
        const double targetDepth=vibratoDepthCents(c.vibrato);const double onset=std::max(.09,std::min(.46,(.18+.12*.33)*(60./tempoBpm)*(1.10-.30*c.vibrato)));
        const double vibEnv=(targetDepth<1.)?0.:std::max(0.,std::min(1.,(v.ageSeconds-onset)/std::max(.08,onset*.75)));
        double vibHz=vibratoRateHz(p,v.note,c.vibrato,c);v.vibJitterPhase+=twoPi*.37/sampleRate;if(v.vibJitterPhase>twoPi)v.vibJitterPhase-=twoPi;vibHz*=1.+(.015+.035*c.vibrato)*std::sin(v.vibJitterPhase);
        v.vibPhase+=twoPi*vibHz/sampleRate;if(v.vibPhase>twoPi)v.vibPhase-=twoPi;double vib=targetDepth*vibEnv*std::sin(v.vibPhase);if(a==(int)Articulation::Harmonic)vib*=.45;if(a==(int)Articulation::Spiccato||a==(int)Articulation::Staccato||a==(int)Articulation::Pizzicato)vib*=.15;
        const double bend=(c.pitchBend-.5)*4.;const double f=v.baseFreq*std::pow(2.,(bend+vib/100.)/12.);v.phase+=twoPi*f/sampleRate;if(v.phase>twoPi)v.phase-=twoPi;v.tremPhase+=twoPi*10.5/sampleRate;if(v.tremPhase>twoPi)v.tremPhase-=twoPi;
        const double ph=v.phase;float bright=toneForPart(p)*(.70f+.55f*c.dynamics);if(a==(int)Articulation::Flautando)bright*=.46f;if(a==(int)Articulation::Harmonic)bright*=1.25f;float s;
        if(a==(int)Articulation::Harmonic)s=float(.35*std::sin(ph)+.75*std::sin(2*ph)+.28*std::sin(4*ph));else s=float(std::sin(ph)+.48*bright*std::sin(2*ph+.12)+.23*bright*std::sin(3*ph+.31)+.10*bright*std::sin(5*ph+.47));
        if(a==(int)Articulation::Tremolo) s*=float(.66+.34*(.5+.5*std::sin(v.tremPhase)));
        if(a==(int)Articulation::Trill) s+=.28f*float(std::sin(ph*std::pow(2.,2./12.)));
        if(a==(int)Articulation::Pizzicato) s*=float(std::exp(-5.5*(1.-v.env)));
        if(a==(int)Articulation::Marcato) s*=1.18f;
        const float gain=.075f*v.velocity*(.20f+.80f*c.dynamics)*c.expression*c.volume*float(v.env);s*=gain;const float pan=panForPart(p),gl=std::sqrt(.5f*(1.f-pan)),gr=std::sqrt(.5f*(1.f+pan));L+=s*gl;R+=s*gr;
    }left[i]+=L;right[i]+=R;}
}
}
