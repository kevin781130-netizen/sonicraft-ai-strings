#include "../src/preview_engine.h"
#include <cassert>
#include <cmath>
#include <iostream>
#include <vector>
using namespace Sonicraft::AIStrings;

static std::vector<float> makePerformance(int block) {
    PreviewEngine engine;
    engine.setSampleRate(48000);
    PartControl control;
    control.continuousGesture=true;
    control.legato=true;
    control.sustain=false;
    control.articulation=static_cast<int>(Articulation::Legato);
    engine.noteOnVoice(0,0,69,.8f,control);
    std::vector<float> mono;
    const auto append=[&](int frames) {
        while(frames>0){
            const int n=std::min(block,frames);
            std::vector<float> left(n,0),right(n,0);
            engine.render(left.data(),right.data(),n);
            for(int i=0;i<n;++i) mono.push_back(left[i]+right[i]);
            frames-=n;
        }
    };
    append(4800);
    engine.noteOnVoice(0,0,72,.8f,control);
    append(9600);
    engine.noteOffVoice(0,0,72);
    append(9600);
    return mono;
}

int main() {
    const auto a=makePerformance(64),b=makePerformance(257);
    assert(a.size()==b.size());
    double energy=0;
    for(size_t i=0;i<a.size();++i){
        assert(std::isfinite(a[i]));
        assert(a[i]==b[i]); // deterministic oscillator, noise and body state across block sizes
        energy+=double(a[i])*a[i];
    }
    assert(energy>0.01);
    // The carried phase/short crossfade must not click sharply at the note boundary.
    assert(std::abs(a[4800]-a[4799])<.15f);
    // Every advertised SONICRAFT preview profile must be reachable, finite and audible.
    for(int instrument=0;instrument<15;++instrument){
        PreviewEngine voice;voice.setSampleRate(48000);voice.setPartInstrument(0,instrument);
        voice.noteOn(0,60,.8f);
        float left[512]{},right[512]{};voice.render(left,right,512);
        double power=0;
        for(int i=0;i<512;++i){assert(std::isfinite(left[i])&&std::isfinite(right[i]));power+=left[i]*left[i]+right[i]*right[i];}
        assert(power>1e-8);
        assert(acousticOverrideIndex(float(instrument+1)/15.f)==instrument);
    }
    assert(acousticOverrideIndex(0.f)==-1);
    // A DAW note-off must release by default; CC64 sustains only while held.
    {
        PreviewEngine voice;voice.setSampleRate(48000);voice.setPartInstrument(0,0);
        PartControl c;assert(!c.sustain);
        float left[512]{},right[512]{};
        voice.noteOnVoice(0,0,69,.8f,c);voice.render(left,right,512);
        voice.noteOffVoice(0,0,69);
        for(int b=0;b<300;++b){std::fill(std::begin(left),std::end(left),0.f);std::fill(std::begin(right),std::end(right),0.f);voice.render(left,right,512);}
        for(float sample:left)assert(std::abs(sample)<1e-5f);

        voice.setPartSustain(0,true);c.sustain=true;
        voice.noteOnVoice(0,0,69,.8f,c);voice.render(left,right,512);
        voice.noteOffVoice(0,0,69);
        voice.render(left,right,512);
        double held=0;for(float sample:left)held+=double(sample)*sample;
        assert(held>1e-8);
        voice.setPartSustain(0,false);
        for(int b=0;b<300;++b){std::fill(std::begin(left),std::end(left),0.f);std::fill(std::begin(right),std::end(right),0.f);voice.render(left,right,512);}
        for(float sample:left)assert(std::abs(sample)<1e-5f);
    }
    std::cout<<"Violin acoustic voice block parity / legato smoke OK\n";
}
