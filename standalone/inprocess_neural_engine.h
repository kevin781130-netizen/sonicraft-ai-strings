#pragma once
#include "realtime_shell_core.h"
#include <array>
#include <cstdint>
#include <memory>
#include <span>
#include <string>
#include <vector>

namespace Sonicraft::InProcess {

constexpr int kRawControls = 33;
constexpr int kFrontierContext = 14;
constexpr int kMaxVoices = 16;
constexpr int kStageChannels = 34;

enum class Solver { Euler, Heun };

struct EngineConfig {
    uint32_t sampleRate = 48000;
    int latentChannels = 64;
    float latentHz = 30.f;
    int codecSampleRate = 48000;
    int stepsAuto = 2;
    int stepsHq = 4;
    float cfgAuto = 1.f;
    float cfgHq = 1.f;
    Solver solver = Solver::Euler;
    int controlFps = 100;
    int maxVoices = kMaxVoices;
};

struct ControlBatch {
    int frames = 0;
    std::vector<float> raw;                  // [1,T,33]
    std::vector<float> vibratoPhysicsKnown; // [1,T]
    std::vector<float> frontierContext;      // [1,14,T]
    std::vector<float> articulationCurve;   // [1,T]
    int64_t instrument = 0;
    int64_t articulation = 0;
    int64_t player = 0;
    std::vector<float> gate;
};

struct RendererInputs {
    std::span<const float> latent;
    std::array<int64_t,3> latentShape{};
    float flowT = 0.f;
    float flowH = 0.f;
    const ControlBatch* controls = nullptr;
};

class NeuralSession {
public:
    virtual ~NeuralSession() = default;
    virtual std::string name() const = 0;
    virtual std::string fingerprint() const = 0;
    virtual bool ready() const = 0;
    virtual bool runRenderer(const RendererInputs& in, std::vector<float>& velocity) = 0;
    virtual bool runDecoder(std::span<const float> latent, std::array<int64_t,3> shape,
                            std::vector<float>& mono, int& sampleRate) = 0;
};

struct EngineRender {
    uint32_t sampleRate = 48000;
    uint32_t frames = 0;
    uint16_t channels = 0;
    std::vector<float> interleaved;
    int voicesRendered = 0;
    int neuralCalls = 0;
    std::string backend;
};

class NativeControlBuilder {
public:
    explicit NativeControlBuilder(int fps=100):fps_(fps){}
    ControlBatch build(const std::vector<ProductShell::TimelineEvent>& allEvents,
                       const std::vector<ProductShell::TimelineEvent>& lane,
                       int part, int64_t startSample, int64_t endSample, uint32_t sampleRate,
                       const ProductShell::Policy& policy, const std::string& fingerprint) const;
private:
    int fps_ = 100;
};

std::vector<std::vector<ProductShell::TimelineEvent>> allocatePolyphonicLanes(
    const std::vector<ProductShell::TimelineEvent>& events, int part, int maxVoices=kMaxVoices);

class InProcessEngine {
public:
    InProcessEngine(std::shared_ptr<NeuralSession> session, EngineConfig cfg={});
    bool ready() const;
    std::string backendName() const;
    const EngineConfig& config() const { return cfg_; }
    bool render(const std::vector<ProductShell::TimelineEvent>& events,
                int64_t startSample, int64_t endSample,
                const ProductShell::Policy& policy,
                EngineRender& out);
private:
    std::shared_ptr<NeuralSession> session_;
    EngineConfig cfg_;
    NativeControlBuilder controls_;
};

// Test-only deterministic session proves the full C++ graph is service/Python independent.
class DeterministicMockSession final : public NeuralSession {
public:
    std::string name() const override { return "cpp-mock"; }
    std::string fingerprint() const override { return "SONICRAFT_V26_CPP_MOCK"; }
    bool ready() const override { return true; }
    bool runRenderer(const RendererInputs& in, std::vector<float>& velocity) override;
    bool runDecoder(std::span<const float> latent, std::array<int64_t,3> shape,
                    std::vector<float>& mono, int& sampleRate) override;
};

} // namespace Sonicraft::InProcess
