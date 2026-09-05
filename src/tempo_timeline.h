#pragma once
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
namespace Sonicraft::AIStrings {
struct TempoPoint { double beat=0.0,bpm=68.0; std::int64_t sample=0; };
class TempoTimelineCapture {
public:
    static constexpr std::size_t kMaxPoints=1024;
    void clear(){count_=0;}
    void observe(double beat,double bpm,std::int64_t sample){
        if(!std::isfinite(beat)||!std::isfinite(bpm)||bpm<20.0||bpm>400.0)return;
        if(count_>0){const auto& p=points_[count_-1];
            if(beat<p.beat-.01){clear();}
            else if(std::abs(p.bpm-bpm)<1e-4 && beat>=p.beat && (beat-p.beat)<.25)return;
        }
        if(count_<kMaxPoints)points_[count_++]={beat,bpm,sample};
        else {
            for(std::size_t i=1;i<kMaxPoints/2;++i)points_[i]=points_[i*2];
            count_=kMaxPoints/2;points_[count_++]={beat,bpm,sample};
        }
    }
    bool sampleAtBeat(double beat,double sampleRate,std::int64_t& out)const{
        if(count_==0||!std::isfinite(beat)||!(sampleRate>0.0))return false;
        const TempoPoint* best=nullptr;
        for(std::size_t i=0;i<count_;++i){
            const auto& p=points_[i];
            if(p.beat<=beat+1e-9)best=&p;else break;
        }
        if(!best)best=&points_[0];
        const double delta=(beat-best->beat)*(60.0/best->bpm)*sampleRate;
        out=best->sample+static_cast<std::int64_t>(std::llround(delta));return true;
    }
    double tempoAtBeat(double beat,double fallback=68.0)const{
        if(count_==0||!std::isfinite(beat))return fallback;
        const TempoPoint* best=nullptr;
        for(std::size_t i=0;i<count_;++i){if(points_[i].beat<=beat+1e-9)best=&points_[i];else break;}
        return best?best->bpm:fallback;
    }
    std::size_t size()const{return count_;}
    const TempoPoint* data()const{return points_.data();}
private:
    std::array<TempoPoint,kMaxPoints> points_{};std::size_t count_=0;
};
}
