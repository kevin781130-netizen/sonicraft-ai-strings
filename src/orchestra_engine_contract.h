#pragma once

#include "orchestra_instruments.h"
#include "dnni_runtime_layout.h"
#include <algorithm>
#include <array>
#include <cstdint>

namespace Sonicraft::AIStrings {

// Stable real-time-safe ABI between the VST3/editor layer and a future SONICRAFT
// orchestra renderer. No proprietary tensor/layout assumptions live here.

enum OrchestraArticulationBit : std::uint32_t {
    kArtSustain       = 1u << 0,
    kArtLegato        = 1u << 1,
    kArtTenuto        = 1u << 2,
    kArtStaccato      = 1u << 3,
    kArtMarcato       = 1u << 4,
    kArtPortamento    = 1u << 5,
    kArtTremolo       = 1u << 6,
    kArtPizzicato     = 1u << 7,
    kArtTrill         = 1u << 8,
    kArtHarmonic      = 1u << 9,
    kArtColLegno      = 1u << 10,
    kArtMute          = 1u << 11,
    kArtFlutterTongue = 1u << 12,
    kArtAccent        = 1u << 13
};

struct OrchestraCurvePoint {
    float beat {0.f};
    float value {0.f};
};

template <std::size_t N>
struct OrchestraCurve {
    std::array<OrchestraCurvePoint, N> point{};
    std::uint16_t count {0};

    void clear() noexcept { count = 0; }

    bool push(float beat, float value) noexcept {
        if (count >= N) return false;
        point[count++] = {beat, value};
        return true;
    }
};

struct OrchestraNote {
    std::uint32_t noteId {0};
    std::uint8_t midiPitch {60};
    std::uint8_t midiChannel {0};
    std::uint32_t articulationBits {kArtSustain};
    float startBeat {0.f};
    float durationBeat {1.f};
    float velocity {.7f};
    float dynamics {.65f};
    float expression {1.f};
    float vibrato {.5f};
    float timbre {.5f};
    float microPitchCents {0.f};
    float attackCharacter {.5f};
    float transition {.5f};
};

struct OrchestraMicMixerState {
    static constexpr int kFeedCount = 16;
    bool enabled {false};
    float masterGain {1.f};
    float outputGain {1.f};
    std::array<float, kFeedCount> feedGain{{
        .25f,.35f,.25f,.45f,.62f,.45f,.28f,.28f,
        .20f,.20f,0.f,.12f,.12f,.06f,.06f,0.f
    }};
};

struct OrchestraPerformanceState {
    OrchestraInstrument instrument {OrchestraInstrument::Violin};
    float tempoBpm {120.f};
    float humanize {.16f};
    float smartDynamics {0.f};
    float smartArticulation {0.f};
    float polyphony {1.f};
    float phraseDirector {1.f};
    float retakeAmount {0.f};
    std::uint32_t retakeSeed {0};
    std::uint32_t retakeTargetMask {0};
    OrchestraCurve<128> dynamicsCurve{};
    OrchestraCurve<128> pitchCurve{};
    OrchestraCurve<128> vibratoCurve{};
    OrchestraMicMixerState mic{};
};

struct OrchestraModelBinding {
    OrchestraInstrument instrument {OrchestraInstrument::Violin};
    bool present {false};
    bool sourceHashVerified {false};
    bool weightsHashVerified {false};
    bool layoutVerified {false};
    std::uint64_t fileSize {0};
    std::uint64_t weightsOffset {0};
    std::uint64_t weightsBytes {0};
    std::uint64_t sharedCoreBytes {0};
    std::uint64_t variableTailBytes {0};
    std::uint64_t tailSubblockBytes {0};
    int candidateMicGroups {0};
    int tailSubblockCount {0};
};

struct OrchestraRenderBlock {
    static constexpr int kMaxNotes = 256;
    std::array<OrchestraNote, kMaxNotes> notes{};
    std::uint16_t noteCount {0};
    OrchestraPerformanceState performance{};
    OrchestraModelBinding model{};

    void clearNotes() noexcept { noteCount = 0; }

    bool pushNote(const OrchestraNote& note) noexcept {
        if (noteCount >= kMaxNotes) return false;
        notes[noteCount++] = note;
        return true;
    }

    bool valid() const noexcept {
        if (!model.present || !model.sourceHashVerified || !model.weightsHashVerified || !model.layoutVerified) return false;
        if (performance.tempoBpm < 1.f || performance.tempoBpm > 1000.f) return false;
        for (std::uint16_t i = 0; i < noteCount; ++i) {
            const auto& n = notes[i];
            if (n.midiPitch > 127 || n.durationBeat <= 0.f) return false;
        }
        return true;
    }
};

} // namespace Sonicraft::AIStrings
