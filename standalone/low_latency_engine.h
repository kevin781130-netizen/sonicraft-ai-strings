#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <vector>

namespace Sonicraft::LowLatency {

struct QuantumDecision {
    int quantumMs=80;
    const char* reason="balanced";
};

class AdaptiveQuantumController {
public:
    void reset();
    QuantumDecision choose(bool freshAttack, double previousRenderMs, bool deadlineMiss, int queuedBlocks);
    int currentMs() const { return currentMs_; }
private:
    int currentMs_=80;
    int stableFast_=0;
    int misses_=0;
};

class MidiTimestampCalibrator {
public:
    void reset(uint32_t sampleRate, int64_t timelineOriginSample=0, uint32_t midiOriginMs=0);
    int64_t sampleFor(uint32_t driverTimestampMs) const;
private:
    uint32_t sampleRate_=48000, midiOriginMs_=0;
    int64_t timelineOrigin_=0;
};

class GlitchGuard {
public:
    explicit GlitchGuard(int rampFrames=48):rampFrames_(std::max(1,rampFrames)){}
    void reset();
    void processStereo(std::vector<float>& interleaved, bool hardRelease=false);
private:
    int rampFrames_=48;
    bool haveLast_=false;
    float lastL_=0.f,lastR_=0.f;
};

} // namespace Sonicraft::LowLatency
