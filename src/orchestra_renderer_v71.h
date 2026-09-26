#pragma once

#include "orchestra_conditioning_contract.h"
#include <array>
#include <cstdint>

namespace Sonicraft::AIStrings {

class OrchestraRendererV71 {
public:
    static constexpr int kMaxVoices = 48;
    static constexpr int kHarmonics = 16;

    void reset(double sampleRate) noexcept;
    void allNotesOff() noexcept;

    bool noteOn(
        int lane,
        int note,
        const MusicalControlFrame& control,
        const OrchestraPerformanceState& performance,
        const OrchestraConditioningFeatures& features) noexcept;

    void noteOff(int lane, int note) noexcept;

    void render(float* left, float* right, std::int32_t samples, float mix) noexcept;

    int activeVoiceCount() const noexcept;
    double sampleRate() const noexcept { return sampleRate_; }

private:
    struct Voice {
        bool active {false};
        bool releasing {false};
        int lane {-1};
        int note {-1};
        OrchestraInstrument instrument {OrchestraInstrument::Violin};
        std::uint32_t articulationBits {kArtSustain};
        float velocity {.7f};
        float dynamics {.65f};
        float expression {1.f};
        float vibrato {.5f};
        float attackCharacter {.5f};
        float transition {.5f};
        float pan {0.f};
        float featureEnergy {0.f};
        double baseFrequency {440.0};
        double phase {0.0};
        double vibratoPhase {0.0};
        double envelope {0.0};
        double ageSeconds {0.0};
        std::array<float, kHarmonics> harmonicGain{};
        std::array<double, kHarmonics> harmonicPhase{};
    };

    Voice* allocateVoice() noexcept;
    static double midiToHz(float note) noexcept;

    std::array<Voice, kMaxVoices> voices_{};
    double sampleRate_ {48000.0};
};

} // namespace Sonicraft::AIStrings
