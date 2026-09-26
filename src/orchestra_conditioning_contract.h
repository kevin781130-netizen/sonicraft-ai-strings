#pragma once

#include "orchestra_engine_contract.h"
#include <array>
#include <cstdint>

namespace Sonicraft::AIStrings {

// SONICRAFT-owned conditioning ABI.
// Widths are informed by observed container boundaries, but all feature semantics and
// transforms are defined by SONICRAFT rather than copied from a proprietary runtime.

struct MusicalControlFrame {
    float midiPitch {69.f};
    float notePhase {0.f};
    float durationBeats {1.f};
    float velocity {.70f};
    float dynamics {.65f};
    float expression {1.f};
    float vibrato {.50f};
    float pitchCents {0.f};
    float transition {.50f};
    float attackCharacter {.50f};
    float phrasePosition {0.f};
    std::uint32_t articulationBits {kArtSustain};
};

struct OrchestraConditioningFeatures {
    static constexpr int kBranch128 = 128;
    static constexpr int kBranch256 = 256;
    static constexpr int kObserved452 = 452;
    static constexpr int kObserved506 = 506;
    static constexpr int kLatent512 = 512;

    std::array<float, kBranch128> branch128{};
    std::array<float, kBranch256> branch256A{};
    std::array<float, kBranch256> branch256B{};
    std::array<float, kBranch256> branch256C{};
    std::array<float, kObserved452> feature452{};
    std::array<float, kObserved506> feature506{};
    std::array<float, kLatent512> latent512{};

    void clear() noexcept {
        branch128.fill(0.f);
        branch256A.fill(0.f);
        branch256B.fill(0.f);
        branch256C.fill(0.f);
        feature452.fill(0.f);
        feature506.fill(0.f);
        latent512.fill(0.f);
    }
};

struct ObservedDnniBoundaryDescriptor {
    static constexpr std::uint64_t kUpstreamFamilyStart = 18'251'776ull;
    static constexpr std::uint64_t kRegularUpstreamModuleBytes = 2'633'728ull;
    static constexpr int kRegularUpstreamModuleCount = 7;
    static constexpr std::uint64_t kFinalUpstreamModuleStart = 36'687'872ull;
    static constexpr std::uint64_t kFinalUpstreamModuleBytes = 2'568'192ull;
    static constexpr std::uint64_t kLeftInterfaceBankStart = 39'256'064ull;

    static constexpr int kHiddenWidth = 512;
    static constexpr int kFinalProjectionOtherWidth = 452;
    static constexpr int kInternalProjectionWidth = 506;

    static constexpr bool boundaryAccountingValid() noexcept {
        return kFinalUpstreamModuleStart + kFinalUpstreamModuleBytes
            == kLeftInterfaceBankStart;
    }
};

// Implementations of this interface are SONICRAFT-owned conditioning models/rules.
// No DNNI producer equation is implied by the interface.
class IOrchestraConditioner {
public:
    virtual ~IOrchestraConditioner() = default;

    virtual void reset(double sampleRate) noexcept = 0;

    virtual bool condition(
        const MusicalControlFrame& control,
        const OrchestraPerformanceState& performance,
        OrchestraConditioningFeatures& out) noexcept = 0;
};

} // namespace Sonicraft::AIStrings
