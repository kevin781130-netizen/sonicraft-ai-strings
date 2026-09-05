#pragma once
#include <array>
#include <atomic>
#include <cstdint>
#include <thread>
#include <vector>
#include <chrono>

namespace Sonicraft::AIStrings {

struct ShadowControls {
    float dyn=.62f,vib=.50f,exp=.90f,vol=.86f,pan=.50f,sus=1.f,leg=1.f,room=.18f,bend=.50f,art=0.f,transition=.50f,tightness=.50f,attack=.38f,speedProfile=0.f;
};


struct TakeJudgeSnapshotV37 {
    uint32_t generation=0;
    int64_t startSample=0;
    uint64_t configToken=0;
    int winner=-1;
    uint8_t validMask=0;
    std::array<float,4> overall{{0,0,0,0}};
    std::array<float,4> dynamics{{0,0,0,0}};
    std::array<float,4> attack{{0,0,0,0}};
    std::array<float,4> transition{{0,0,0,0}};
    std::array<float,4> stability{{0,0,0,0}};
    std::array<float,4> safety{{0,0,0,0}};
    std::array<float,4> personal{{0,0,0,0}};
    uint32_t profileHash32=0; float profileConfidence=0.f;
    std::array<float,5> profileWeights{{0,0,0,0,0}};
};

struct ShadowEvent {
    int64_t projectSample=0;
    uint8_t type=0, part=0, note=0, articulation=0;
    float velocity=0.f, tempoBpm=68.f;
    ShadowControls controls{};
};

class ShadowAudioCache {
public:
    static constexpr int kSlots=4;
    struct Slot {
        std::atomic<uint32_t> readers{0};
        std::atomic<bool> writing{false};
        int64_t startSample=0;
        uint32_t frames=0;
        uint32_t sampleRate=0;
        uint16_t channels=2;
        uint64_t generation=0;
        std::vector<float> interleaved;
    };
    bool install(int64_t startSample,uint32_t sampleRate,uint32_t frames,uint16_t channels,std::vector<float>&& interleaved);
    void mix(float* left,float* right,float* const* auxLeft,float* const* auxRight,int auxPairs,int32_t n,int64_t projectStart,float wet,float crossfadeMs=22.f) noexcept;
    uint64_t latestGeneration() const noexcept { return generation.load(std::memory_order_acquire); }
private:
    std::array<Slot,kSlots> slots{};
    std::atomic<int> active{-1};
    std::atomic<uint64_t> generation{0};
};

template<typename T, size_t N>
class SpscRing {
public:
    bool push(const T& v) noexcept {
        const auto w=write.load(std::memory_order_relaxed), next=(w+1)%N;
        if(next==read.load(std::memory_order_acquire)) return false;
        data[w]=v; write.store(next,std::memory_order_release); return true;
    }
    bool pop(T& v) noexcept {
        const auto r=read.load(std::memory_order_relaxed);
        if(r==write.load(std::memory_order_acquire)) return false;
        v=data[r]; read.store((r+1)%N,std::memory_order_release); return true;
    }
private:
    std::array<T,N> data{};
    std::atomic<size_t> write{0},read{0};
};

class ShadowRenderClient {
public:
    enum EventType : uint8_t { NoteOn=1, NoteOff=2, Keyswitch=3, Control=4, Reset=5 };
    ShadowRenderClient();
    ~ShadowRenderClient();
    ShadowRenderClient(const ShadowRenderClient&)=delete;
    ShadowRenderClient& operator=(const ShadowRenderClient&)=delete;

    void configure(double sampleRate) noexcept { sr.store(sampleRate,std::memory_order_release); }
    void setRuntimeState(int m,float mix,float look,float assist,float performanceStyle,float smartDynamics,float smartArticulation,float retakeTarget,float retakeAmount,float retakeNonce,float stagePerspective,float polyphony,float midiAuthorityLock,float phraseDirector,float ensembleLooseness,bool multiOut,bool isPlaying,int64_t projectStart,int32_t blockSamples,float tempo) noexcept;
    void pushMidi(EventType type,int64_t projectSample,int part,int note,int articulation,float velocity,float tempo,const ShadowControls& c) noexcept;
    void pushControl(int64_t projectSample,int part,float tempo,const ShadowControls& c) noexcept;
    void resetTimeline(int64_t projectSample) noexcept;
    void mix(float* left,float* right,float* const* auxLeft,float* const* auxRight,int auxPairs,int32_t n,int64_t projectStart) noexcept;
    void requestTakeJudge(int64_t startSample,int64_t endSample,float baseNonce,uint8_t favoriteMask,uint8_t rejectMask,uint64_t configToken,uint32_t policyFlags,int judgeMode,float judgeTempo,float judgeLookAhead,bool personalEnabled=true,float personalStrength=1.f) noexcept;
    TakeJudgeSnapshotV37 takeJudgeSnapshot() const noexcept;

    bool serviceReady() const noexcept { return ready.load(std::memory_order_acquire); }
    uint32_t cacheHits() const noexcept { return hitCount.load(std::memory_order_relaxed); }
    uint32_t renders() const noexcept { return renderCount.load(std::memory_order_relaxed); }
private:
    void workerMain();
    bool requestRender(const std::vector<ShadowEvent>& events,int64_t start,int64_t end,uint64_t requestId,int mode,float tempo,float lookahead);
    bool requestJudgeRender(const std::vector<ShadowEvent>& events,int64_t start,int64_t end,uint64_t requestId,int mode,float tempo,float lookahead,float baseNonce,uint8_t favoriteMask,uint8_t rejectMask,uint64_t configToken,uint32_t policyFlags,bool personalEnabled,float personalStrength);
    std::thread worker;
    std::atomic<bool> stop{false},ready{false},playing{false};
    std::atomic<int> mode{0},assistProfile{1},performanceStyle{0},retakeTarget{0},retakeNonce{0},stagePerspective{1};
    std::atomic<bool> smartDynamics{false},smartArticulation{false},polyphony{true},midiAuthorityLock{true},phraseDirector{true},multiOut{false};
    std::atomic<float> aiMix{0.f},lookAhead{.35f},tempoBpm{68.f},retakeAmount{0.f},ensembleLooseness{.18f};
    std::atomic<double> sr{48000.0};
    std::atomic<int64_t> latestProjectStart{0},latestProjectEnd{0};
    std::atomic<uint32_t> hitCount{0},renderCount{0};
    std::atomic<intptr_t> activeSocket{-1};
    std::atomic<bool> judgePending{false};
    std::atomic<int64_t> judgeStart{0},judgeEnd{0};
    std::atomic<float> judgeBaseNonce{0.f};
    std::atomic<uint32_t> judgeReviewMasks{0};
    std::atomic<uint32_t> judgeGeneration{0};
    std::atomic<uint64_t> judgePendingToken{0},judgeResultToken{0};
    std::atomic<uint32_t> judgePendingFlags{0};
    std::atomic<int> judgePendingMode{1};
    std::atomic<float> judgePendingTempo{68.f},judgePendingLook{.35f};
    std::atomic<bool> judgePendingPersonalEnabled{true}; std::atomic<float> judgePendingPersonalStrength{1.f};
    std::atomic<int64_t> judgeResultStart{0};
    std::atomic<int> judgeWinner{-1};
    std::atomic<uint32_t> judgeValidMask{0};
    std::array<std::atomic<float>,4> judgeOverall{},judgeDynamics{},judgeAttack{},judgeTransition{},judgeStability{},judgeSafety{},judgePersonal{};
    std::atomic<uint32_t> judgeProfileHash32{0}; std::atomic<float> judgeProfileConfidence{0.f}; std::array<std::atomic<float>,5> judgeProfileWeights{};
    SpscRing<ShadowEvent,4096> eventRing;
    ShadowAudioCache cache;
};

} // namespace
