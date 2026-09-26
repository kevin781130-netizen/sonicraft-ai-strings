#include "orchestra_conditioner_v71.h"

#include <cassert>
#include <cmath>
#include <iostream>

using namespace Sonicraft::AIStrings;

template <std::size_t N>
static double distance(const std::array<float,N>& a, const std::array<float,N>& b) {
    double s=0.0;
    for(std::size_t i=0;i<N;++i){
        const double d=double(a[i])-double(b[i]);
        s+=d*d;
    }
    return std::sqrt(s);
}

template <std::size_t N>
static bool finiteBounded(const std::array<float,N>& a) {
    for(float v:a) if(!std::isfinite(v)||std::abs(v)>1.0001f) return false;
    return true;
}

int main() {
    OrchestraConditionerV71 conditioner;
    conditioner.reset(48000.0);

    OrchestraPerformanceState performance{};
    performance.instrument=OrchestraInstrument::Violin;
    performance.tempoBpm=120.f;
    performance.humanize=.16f;
    performance.smartDynamics=.75f;
    performance.smartArticulation=.8f;

    MusicalControlFrame a{};
    a.midiPitch=69.f;
    a.velocity=.70f;
    a.dynamics=.65f;
    a.expression=1.f;
    a.vibrato=.50f;
    a.articulationBits=kArtSustain;

    OrchestraConditioningFeatures fa{},fb{};
    assert(conditioner.condition(a,performance,fa));
    assert(conditioner.condition(a,performance,fb));
    assert(distance(fa.latent512,fb.latent512)==0.0);
    assert(finiteBounded(fa.branch128));
    assert(finiteBounded(fa.feature452));
    assert(finiteBounded(fa.feature506));
    assert(finiteBounded(fa.latent512));

    auto pitch=a;
    pitch.midiPitch=76.f;
    OrchestraConditioningFeatures fp{};
    assert(conditioner.condition(pitch,performance,fp));
    assert(distance(fa.feature506,fp.feature506)>0.1);

    auto dyn=a;
    dyn.dynamics=.20f;
    OrchestraConditioningFeatures fd{};
    assert(conditioner.condition(dyn,performance,fd));
    assert(distance(fa.feature506,fd.feature506)>0.1);

    auto art=a;
    art.articulationBits=kArtStaccato|kArtAccent;
    OrchestraConditioningFeatures fr{};
    assert(conditioner.condition(art,performance,fr));
    assert(distance(fa.branch128,fr.branch128)>1.0);

    auto perf2=performance;
    perf2.instrument=OrchestraInstrument::Trombone;
    OrchestraConditioningFeatures fi{};
    assert(conditioner.condition(a,perf2,fi));
    assert(distance(fa.latent512,fi.latent512)>0.1);

    std::cout<<"orchestra_conditioner_v71_smoke: ok\n";
    return 0;
}
