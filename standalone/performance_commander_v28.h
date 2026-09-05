#pragma once
#include <array>
#include <cstdint>
#include <vector>
namespace Sonicraft::PerformanceCommanderV28 {
enum class RetakeTarget:int { Off=0,Timbre=1,Dynamics=2,Vibrato=3,MicroPitch=4,Timing=5,BowAttack=6,All=7 };
struct Policy { bool authorityLock=true; bool phraseDirector=true; float ensembleLooseness=.18f; };
class SmartDivisi {
public:
    SmartDivisi();
    int noteOn(int inputChannel,int note);
    int noteOff(int inputChannel,int note);
    void reset();
    const std::array<int,4>& activeCounts() const { return active_; }
private:
    int choose(int note) const;
    std::array<std::array<int8_t,128>,16> owner_{};
    std::array<int,4> active_{{0,0,0,0}};
};
uint32_t encodePolicyFlags(int assist,int style,bool smartDynamics,bool smartArticulation,bool polyphony,RetakeTarget retake,int nonce,int perspective,float amount,bool multiOut,const Policy& p);
struct TakeDescriptor { int seed=0; RetakeTarget target=RetakeTarget::Off; bool changesWrittenPitch=false; };
std::vector<TakeDescriptor> buildTakeMatrix(int seedBase,int count,RetakeTarget target,const Policy& p);
} // namespace
