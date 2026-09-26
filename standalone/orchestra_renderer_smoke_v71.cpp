#include "orchestra_conditioner_v71.h"
#include "orchestra_renderer_v71.h"

#include <array>
#include <cassert>
#include <cmath>
#include <iostream>
#include <vector>

using namespace Sonicraft::AIStrings;

static double rms(const float* x, int n) {
    double s=0.0;
    for(int i=0;i<n;++i) s+=double(x[i])*double(x[i]);
    return std::sqrt(s/double(n));
}

static double zeroCrossPitch(const float* x, int n, double sr) {
    int crossings=0;
    for(int i=1;i<n;++i)
        if(x[i-1] <= 0.f && x[i] > 0.f) ++crossings;
    return double(crossings)*sr/double(n);
}

int main() {
    constexpr double sr=48000.0;
    constexpr int n=48000;
    OrchestraConditionerV71 conditioner;
    OrchestraRendererV71 renderer;
    conditioner.reset(sr);
    renderer.reset(sr);

    OrchestraPerformanceState perf{};
    perf.instrument=OrchestraInstrument::Violin;
    perf.tempoBpm=120.f;

    MusicalControlFrame frame{};
    frame.midiPitch=69.f;
    frame.velocity=.72f;
    frame.dynamics=.65f;
    frame.expression=.95f;
    frame.vibrato=.35f;
    frame.articulationBits=kArtSustain;

    OrchestraConditioningFeatures features{};
    assert(conditioner.condition(frame,perf,features));
    assert(renderer.noteOn(0,69,frame,perf,features));
    assert(renderer.activeVoiceCount()==1);

    std::vector<float> left(n,0.f);
    std::vector<float> right(n,0.f);
    renderer.render(left.data(),right.data(),n,1.f);
    const double onRms=rms(left.data()+4096,n-4096);
    assert(std::isfinite(onRms));
    assert(onRms>0.005);
    assert(onRms<0.5);

    const double coarsePitch=zeroCrossPitch(left.data()+12000,24000,sr);
    assert(coarsePitch>300.0 && coarsePitch<3000.0);

    renderer.noteOff(0,69);
    constexpr int releaseN=int(sr*4.0);
    std::vector<float> releaseL(releaseN,0.f);
    std::vector<float> releaseR(releaseN,0.f);
    renderer.render(releaseL.data(),releaseR.data(),releaseN,1.f);
    assert(renderer.activeVoiceCount()==0);
    assert(rms(releaseL.data()+releaseN-12000,12000)<0.0005);

    perf.instrument=OrchestraInstrument::Trombone;
    frame.midiPitch=57.f;
    assert(conditioner.condition(frame,perf,features));
    assert(renderer.noteOn(1,57,frame,perf,features));
    std::vector<float> brassL(8192,0.f);
    std::vector<float> brassR(8192,0.f);
    renderer.render(brassL.data(),brassR.data(),int(brassL.size()),1.f);
    assert(rms(brassL.data(),int(brassL.size()))>0.001);

    std::cout<<"orchestra_renderer_v71_smoke: ok rms="<<onRms
             <<" coarsePitch="<<coarsePitch<<"\n";
    return 0;
}
