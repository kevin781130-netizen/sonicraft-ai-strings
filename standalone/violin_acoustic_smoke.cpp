#include "../src/preview_engine.h"
#include "../src/acoustic_performance.h"
#include "../src/acoustic_stage.h"
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
    // Every voice shares the same DAW ABI, including all keyswitch articulations,
    // active CC modulation, overlapping notes and common offline sample rates.
    for(double rate:{44100.0,48000.0,96000.0})for(int instrument=0;instrument<15;++instrument){
        for(int art=0;art<kArticulationCount;++art){
            PreviewEngine voice;voice.setSampleRate(rate);voice.setPartInstrument(0,instrument);
            PartControl c;c.articulation=art;c.sustain=false;
            voice.noteOnVoice(0,0,60,.8f,c);
            voice.noteOnVoice(0,1,67,.7f,c);
            double power=0;
            for(int b=0;b<5;++b){
                float left[256]{},right[256]{};
                if(b==2){c.dynamics=.3f;c.expression=.55f;c.pitchBend=.7f;voice.updateVoiceLaneControl(0,c);}
                voice.render(left,right,256);
                for(int i=0;i<256;++i){assert(std::isfinite(left[i])&&std::isfinite(right[i]));power+=double(left[i])*left[i]+double(right[i])*right[i];}
            }
            assert(power>1e-9);
            voice.noteOffVoice(0,0,60);voice.noteOffVoice(0,1,67);
        }
    }
    for(int instrument=0;instrument<15;++instrument){
        double signatures[3]{};
        for(int variant=0;variant<3;++variant){
            const int players=variant==0?1:(variant==1?4:16);
            PreviewEngine voice;voice.setSampleRate(48000);voice.setPartInstrument(0,instrument);
            PartControl c;c.sustain=false;
            voice.noteOnVoice(0,0,60,.7f,c,players);
            double weighted=0;
            for(int b=0;b<8;++b){
                float left[256]{},right[256]{};voice.render(left,right,256);
                for(int i=0;i<256;++i){
                    assert(std::isfinite(left[i])&&std::isfinite(right[i]));
                    assert(std::abs(left[i])<1.f&&std::abs(right[i])<1.f);
                    weighted+=(double(left[i])-.6*right[i])*(1+(i%13)*.01);
                }
            }
            signatures[variant]=weighted;
            voice.noteOffVoice(0,0,60);
        }
        assert(std::abs(signatures[0]-signatures[1])>1e-5);
        assert(std::abs(signatures[1]-signatures[2])>1e-5);
    }
    {
        PreviewEngine section;section.setSampleRate(48000);section.setPartInstrument(0,2);
        PartControl c;c.sustain=false;
        for(int note=60;note<68;++note)section.noteOnVoice(0,note-60,note,.6f,c,16);
        float left[512]{},right[512]{};section.render(left,right,512);
        double power=0;for(float x:left){assert(std::isfinite(x));power+=double(x)*x;}
        assert(power>1e-7);
        for(int note=60;note<68;++note)section.noteOffVoice(0,note-60,note);
    }
    {
        PartControl c;
        const auto manual=shapeAcousticPerformance(c,0,0,72,60,.9f,false,0,0.f,.27f,true);
        assert(manual.dynamics==c.dynamics && manual.vibrato==c.vibrato && manual.pitchBend==c.pitchBend);
        const auto smart=shapeAcousticPerformance(c,0,0,72,60,.9f,true,0,0.f,.27f,true);
        assert(smart.dynamics>c.dynamics);
        const auto timbre=shapeAcousticPerformance(c,0,0,72,60,.9f,false,1,1.f,.27f,true);
        assert(timbre.toneColor!=1.f);
        const auto locked=shapeAcousticPerformance(c,0,0,72,60,.9f,false,4,1.f,.27f,true);
        const auto unlocked=shapeAcousticPerformance(c,0,0,72,60,.9f,false,4,1.f,.27f,false);
        assert(locked.pitchBend==c.pitchBend && unlocked.pitchBend!=c.pitchBend);
        assert(timbre.toneColor==shapeAcousticPerformance(c,0,0,72,60,.9f,false,1,1.f,.27f,true).toneColor);
    }
    {
        float masterL[4]{.3f,.2f,-.1f,.4f},masterR[4]{.1f,-.2f,.3f,.2f};
        float spotL[4]{},spotR[4]{},galleryL[4]{},galleryR[4]{};
        std::array<float*,16> feedsL{},feedsR{};
        feedsL[0]=spotL;feedsR[0]=spotR;
        feedsL[15]=galleryL;feedsR[15]=galleryR;
        renderAcousticStageFeeds(masterL,masterR,feedsL,feedsR,4);
        assert(std::isfinite(spotL[0])&&std::isfinite(galleryR[0]));
        assert(spotL[0]!=galleryL[0] && spotR[1]!=galleryR[1]);
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
