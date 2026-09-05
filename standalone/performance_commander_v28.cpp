#include "performance_commander_v28.h"
#include <algorithm>
#include <cmath>
namespace Sonicraft::PerformanceCommanderV28 {
SmartDivisi::SmartDivisi(){reset();}
void SmartDivisi::reset(){for(auto&x:owner_)x.fill(0);active_.fill(0);}
int SmartDivisi::choose(int note) const {const int pref=note<=52?3:(note<=60?2:(note<=67?1:0));static constexpr int center[4]={76,67,60,48};int best=pref,bestCost=active_[pref]*5+std::abs(note-center[pref])/5;for(int p=0;p<4;++p){int cost=active_[p]*5+std::abs(note-center[p])/5+(p<pref?2:0);if(cost<bestCost){best=p;bestCost=cost;}}return best;}
int SmartDivisi::noteOn(int ch,int note){ch=std::clamp(ch,0,15);note=std::clamp(note,0,127);int p=choose(note);owner_[ch][note]=int8_t(p+1);++active_[p];return p;}
int SmartDivisi::noteOff(int ch,int note){ch=std::clamp(ch,0,15);note=std::clamp(note,0,127);int o=owner_[ch][note];if(o<=0)return -1;int p=o-1;owner_[ch][note]=0;active_[p]=std::max(0,active_[p]-1);return p;}
uint32_t encodePolicyFlags(int assist,int style,bool sd,bool sa,bool poly,RetakeTarget rt,int nonce,int perspective,float amount,bool multi,const Policy&p){return uint32_t(std::clamp(assist,0,2))|(uint32_t(std::clamp(style,0,5))<<2)|(uint32_t(sd)<<5)|(uint32_t(sa)<<6)|(uint32_t(poly)<<7)|(uint32_t(std::clamp(int(rt),0,7))<<8)|(uint32_t(std::clamp(nonce,0,255))<<11)|(uint32_t(std::clamp(perspective,0,3))<<19)|(uint32_t(std::clamp(int(amount*15.f+.5f),0,15))<<21)|(uint32_t(multi)<<25)|(uint32_t(p.authorityLock)<<26)|(uint32_t(p.phraseDirector)<<27)|(uint32_t(std::clamp(int(p.ensembleLooseness*15.f+.5f),0,15))<<28);}
std::vector<TakeDescriptor> buildTakeMatrix(int seedBase,int count,RetakeTarget target,const Policy&p){count=std::clamp(count,1,32);std::vector<TakeDescriptor> out;out.reserve(size_t(count));for(int i=0;i<count;++i){TakeDescriptor d;d.seed=(seedBase+i)&255;d.target=target;d.changesWrittenPitch=(target==RetakeTarget::MicroPitch||target==RetakeTarget::All)&&!p.authorityLock;out.push_back(d);}return out;}
} // namespace
