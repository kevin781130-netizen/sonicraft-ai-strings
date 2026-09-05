#pragma once
#include <array>
#include <cmath>
#include <cstdint>
#include "articulations.h"
namespace Sonicraft::AIStrings {
enum class Part : uint8_t { Violin1=0, Violin2=1, Viola=2, Cello=3 };
struct PartControl {
    float dynamics=.62f,vibrato=.50f,expression=.90f,volume=.86f,pan=.50f,room=.18f,pitchBend=.50f;
    bool sustain=true,legato=true; int articulation=0;
    float transitionSpeed=.50f,shortTightness=.50f,attackCharacter=.38f,speedProfile=0.f;
    bool continuousGesture=false;
};
struct Voice {
    bool active=false; int note=-1,channel=0,lane=-1,articulation=0; double phase=0.0,vibPhase=0.0,tremPhase=0.0,vibJitterPhase=0.0;
    double env=0.0,target=0.0,baseFreq=440.0,ageSeconds=0.0; float velocity=0.8f; bool releasing=false,keyReleased=false;
    PartControl localControl{};
};
class PreviewEngine {
public:
    static constexpr int kMaxVoices=48,kParts=4;
    void setSampleRate(double sr){sampleRate=sr>1000.0?sr:48000.0;}
    void setTempo(double bpm){tempoBpm=bpm>=24.0&&bpm<=300.0?bpm:tempoBpm;}
    void setHumanize(float v){humanize=clamp01(v);}
    void setPartDynamics(int p,float v){if(validPart(p))ctl[p].dynamics=clamp01(v);} void setPartVibrato(int p,float v){if(validPart(p))ctl[p].vibrato=clamp01(v);}
    void setPartExpression(int p,float v){if(validPart(p))ctl[p].expression=clamp01(v);} void setPartVolume(int p,float v){if(validPart(p))ctl[p].volume=clamp01(v);}
    void setPartPan(int p,float v){if(validPart(p))ctl[p].pan=clamp01(v);} void setPartRoom(int p,float v){if(validPart(p))ctl[p].room=clamp01(v);}
    void setPartPitchBend(int p,float v){if(validPart(p))ctl[p].pitchBend=clamp01(v);} void setPartLegato(int p,bool v){if(validPart(p))ctl[p].legato=v;}
    void setPartArticulation(int p,int v){if(validPart(p))ctl[p].articulation=std::max(0,std::min(kArticulationCount-1,v));}
    void setPartTransitionSpeed(int p,float v){if(validPart(p))ctl[p].transitionSpeed=clamp01(v);} void setPartShortTightness(int p,float v){if(validPart(p))ctl[p].shortTightness=clamp01(v);}
    void setPartAttackCharacter(int p,float v){if(validPart(p))ctl[p].attackCharacter=clamp01(v);} void setPartSpeedProfile(int p,float v){if(validPart(p))ctl[p].speedProfile=clamp01(v);}
    void setPartSustain(int p,bool v);
    void noteOn(int channel,int note,float velocity);
    void noteOff(int channel,int note);
    void noteOnVoice(int part,int lane,int note,float velocity,const PartControl& control);
    void noteOffVoice(int part,int lane,int note);
    void updateVoiceLaneControl(int lane,const PartControl& control);
    void render(float* left,float* right,int32_t n); void allNotesOff();
private:
    static float clamp01(float v){return v<0.f?0.f:(v>1.f?1.f:v);} static bool validPart(int p){return p>=0&&p<kParts;}
    static double midiToHz(int n){return 440.0*std::pow(2.0,(n-69)/12.0);} float panForPart(int p)const;float toneForPart(int p)const;Voice* allocateVoice();
    double transitionSeconds(int articulation,const PartControl& c) const; double vibratoDepthCents(float cc3) const; double vibratoRateHz(int part,int note,float cc3,const PartControl& c) const;
    std::array<Voice,kMaxVoices> voices{};std::array<PartControl,kParts> ctl{};double sampleRate=48000.0,tempoBpm=68.0;float humanize=.16f;
};
}
