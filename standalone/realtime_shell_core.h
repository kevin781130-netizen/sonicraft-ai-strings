#pragma once
#include <array>
#include <cstdint>
#include <mutex>
#include <string>
#include <vector>

namespace Sonicraft::ProductShell {

struct Controls {
    float dyn=.62f, vib=.50f, exp=.90f, vol=.86f, pan=.50f, sus=1.f, leg=1.f,
          room=.18f, bend=.50f, art=0.f, transition=.50f, tightness=.50f,
          attack=.38f, speedProfile=0.f;
};
struct Policy {
    int mode=1;              // 1=AUTO, 2=HQ. LIVE belongs to the local preview path.
    int assist=1;            // 0 manual, 1 assist, 2 auto
    int style=0;             // neutral/adagio/allegro/con-fuoco/pop/ballade
    bool smartDynamics=false;
    bool smartArticulation=false;
    bool polyphony=true;
    int retakeTarget=0;      // off/timbre/dynamics/vibrato/micro-pitch/timing/bow-attack/all
    float retakeAmount=0.f;
    int retakeNonce=0;
    int stagePerspective=1;
    float tempo=72.f;
    float lookahead=.12f;
    bool multiOut=true;
    bool midiAuthorityLock=true;
    bool phraseDirector=true;
    float ensembleLooseness=.18f;
};
struct TimelineEvent {
    int64_t sample=0;
    uint8_t type=0, part=0, note=0, articulation=0;
    float velocity=0.f, tempo=72.f;
    Controls controls{};
};
struct RenderAudio {
    uint32_t sampleRate=0, frames=0;
    uint16_t channels=0;
    uint16_t status=0;
    std::vector<float> interleaved;
};
struct MixerState {
    float master=1.f;
    std::array<float,16> feed{}; // v2.8: 16 virtual scoring feeds; default master-only prevents double summing.
    float output=.90f;
};

class Timeline {
public:
    void reset();
    void setSelectedPart(int p);
    int selectedPart() const;
    void setArticulation(int part,int articulation);
    int articulation(int part) const;
    void pushMidiShort(uint8_t status,uint8_t data1,uint8_t data2,int64_t sample,float tempo);
    void pushNote(bool on,int part,int note,int velocity,int64_t sample,float tempo);
    std::vector<TimelineEvent> contextFor(int64_t start,int64_t end,int64_t lookbackSamples) const;
    bool anyActiveNotes() const;
    std::array<Controls,4> controlsSnapshot() const;
private:
    mutable std::mutex mu;
    int selected=0;
    std::array<int,4> arts{{0,0,0,0}};
    std::array<Controls,4> ctrl{};
    std::array<std::array<bool,128>,4> active{};
    std::array<std::array<bool,128>,4> deferredOff{};
    std::array<bool,4> sustainDown{{false,false,false,false}};
    std::vector<TimelineEvent> events;
};

class RendererClient {
public:
    RendererClient(std::string host="127.0.0.1",int port=49337):host_(std::move(host)),port_(port){}
    bool ping(uint32_t sampleRate=48000) const;
    bool render(const std::vector<TimelineEvent>& events,int64_t start,int64_t end,uint32_t sampleRate,
                const Policy& policy,uint64_t requestId,RenderAudio& out) const;
private:
    std::string host_; int port_;
};

std::vector<float> mixToStereo(const RenderAudio& audio,const MixerState& mixer);
bool writePcm16Wav(const std::string& path,const std::vector<float>& stereo,uint32_t sampleRate);
const char* feedName(int i);

} // namespace Sonicraft::ProductShell
