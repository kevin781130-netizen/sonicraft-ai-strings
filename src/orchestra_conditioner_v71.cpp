#include "orchestra_conditioner_v71.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>

namespace Sonicraft::AIStrings {
namespace {

constexpr float kPi = 3.14159265358979323846f;

float clamp01(float v) noexcept {
    return std::clamp(std::isfinite(v) ? v : 0.f, 0.f, 1.f);
}

float clampSigned(float v) noexcept {
    return std::clamp(std::isfinite(v) ? v : 0.f, -1.f, 1.f);
}

float normalizedPitch(float midiPitch, float cents) noexcept {
    const float semitone = (std::isfinite(midiPitch) ? midiPitch : 60.f)
                         + (std::isfinite(cents) ? cents : 0.f) / 100.f;
    return std::clamp((semitone - 60.f) / 60.f, -1.f, 1.f);
}

float articulationDensity(std::uint32_t bits) noexcept {
    unsigned count = 0;
    for (int i = 0; i < 14; ++i)
        count += (bits >> i) & 1u;
    return static_cast<float>(count) / 14.f;
}

template <std::size_t N>
void fillHarmonicBank(
    std::array<float, N>& out,
    const std::array<float, 16>& base,
    float familyPhase) noexcept
{
    for (std::size_t i = 0; i < N; ++i) {
        const float fi = static_cast<float>(i + 1);
        const std::size_t a = (i * 5 + 1) & 15u;
        const std::size_t b = (i * 9 + 3) & 15u;
        const std::size_t c = (i * 13 + 7) & 15u;
        const std::size_t d = (i * 3 + 11) & 15u;

        const float p0 = familyPhase + fi * 0.0174532925f;
        const float p1 = familyPhase * 1.7f + fi * 0.01171875f;
        const float p2 = familyPhase * 0.7f + fi * 0.0234375f;
        const float p3 = familyPhase * 2.3f + fi * 0.0078125f;

        const float v =
            0.42f * std::sin((1.f + float(a)) * base[a] * kPi + p0) +
            0.28f * std::cos((1.f + float(b)) * base[b] * kPi + p1) +
            0.19f * std::sin((1.f + float(c)) * base[c] * (0.5f * kPi) + p2) +
            0.11f * std::cos((1.f + float(d)) * base[d] * (0.75f * kPi) + p3);

        out[i] = std::tanh(v);
    }
}

template <std::size_t N>
bool finiteBounded(const std::array<float, N>& a) noexcept {
    for (float v : a) {
        if (!std::isfinite(v) || std::abs(v) > 1.0001f)
            return false;
    }
    return true;
}

} // namespace

void OrchestraConditionerV71::reset(double sampleRate) noexcept {
    sampleRate_ = (std::isfinite(sampleRate) && sampleRate > 1000.0)
        ? sampleRate
        : 48000.0;
}

bool OrchestraConditionerV71::condition(
    const MusicalControlFrame& control,
    const OrchestraPerformanceState& performance,
    OrchestraConditioningFeatures& out) noexcept
{
    out.clear();

    const int instrumentIndex = std::clamp(
        static_cast<int>(performance.instrument),
        0,
        kOrchestraInstrumentCount - 1);

    const float pitch = normalizedPitch(control.midiPitch, control.pitchCents);
    const float notePhase = clamp01(control.notePhase);
    const float duration = std::clamp(
        std::isfinite(control.durationBeats) ? control.durationBeats : 1.f,
        0.f, 64.f) / 64.f;
    const float velocity = clamp01(control.velocity);
    const float dynamics = clamp01(control.dynamics);
    const float expression = clamp01(control.expression);
    const float vibrato = clamp01(control.vibrato);
    const float transition = clamp01(control.transition);
    const float attack = clamp01(control.attackCharacter);
    const float phrase = clamp01(control.phrasePosition);
    const float tempo = std::clamp(
        std::isfinite(performance.tempoBpm) ? performance.tempoBpm : 120.f,
        20.f, 400.f);
    const float tempoNorm = std::log2(tempo / 120.f) / 2.f;
    const float instrument = static_cast<float>(instrumentIndex)
        / static_cast<float>(kOrchestraInstrumentCount - 1);
    const float artDensity = articulationDensity(control.articulationBits);

    std::array<float, 16> base {{
        pitch,
        notePhase * 2.f - 1.f,
        duration,
        velocity * 2.f - 1.f,
        dynamics * 2.f - 1.f,
        expression * 2.f - 1.f,
        vibrato * 2.f - 1.f,
        transition * 2.f - 1.f,
        attack * 2.f - 1.f,
        phrase * 2.f - 1.f,
        clampSigned(tempoNorm),
        instrument * 2.f - 1.f,
        artDensity * 2.f - 1.f,
        clamp01(performance.humanize) * 2.f - 1.f,
        clamp01(performance.smartDynamics) * 2.f - 1.f,
        clamp01(performance.smartArticulation) * 2.f - 1.f,
    }};

    fillHarmonicBank(out.branch128, base, 0.37f);
    fillHarmonicBank(out.branch256A, base, 1.13f);
    fillHarmonicBank(out.branch256B, base, 2.07f);
    fillHarmonicBank(out.branch256C, base, 3.19f);

    // Keep a compact set of direct, interpretable controls at the head of branch128.
    const std::array<float, 12> direct {{
        pitch,
        velocity * 2.f - 1.f,
        dynamics * 2.f - 1.f,
        expression * 2.f - 1.f,
        vibrato * 2.f - 1.f,
        transition * 2.f - 1.f,
        attack * 2.f - 1.f,
        phrase * 2.f - 1.f,
        clampSigned(tempoNorm),
        instrument * 2.f - 1.f,
        notePhase * 2.f - 1.f,
        duration,
    }};
    for (std::size_t i = 0; i < direct.size(); ++i)
        out.branch128[i] = direct[i];

    // Explicit articulation indicators are SONICRAFT-owned semantics.
    for (int bit = 0; bit < 14; ++bit)
        out.branch128[16 + bit] =
            (control.articulationBits & (1u << bit)) ? 1.f : -1.f;

    // Observed-width buffers are generated from SONICRAFT branches, not from a
    // proprietary producer equation. Fixed index permutations keep the transform
    // deterministic and real-time safe without a stored learned matrix.
    for (std::size_t i = 0; i < out.feature452.size(); ++i) {
        const float a = out.branch256A[i & 255u];
        const float b = out.branch256B[(i * 5 + 17) & 255u];
        const float c = out.branch128[(i * 7 + 11) & 127u];
        out.feature452[i] = std::tanh(0.50f * a + 0.32f * b + 0.18f * c);
    }

    for (std::size_t i = 0; i < out.feature506.size(); ++i) {
        const float a = out.branch256B[i & 255u];
        const float b = out.branch256C[(i * 3 + 29) & 255u];
        const float c = out.feature452[(i * 11 + 7) % out.feature452.size()];
        out.feature506[i] = std::tanh(0.44f * a + 0.31f * b + 0.25f * c);
    }

    for (std::size_t i = 0; i < out.latent512.size(); ++i) {
        const float a = out.feature506[i % out.feature506.size()];
        const float b = out.branch256A[(i * 13 + 5) & 255u];
        const float c = out.branch128[(i * 3 + 1) & 127u];
        out.latent512[i] = std::tanh(0.58f * a + 0.27f * b + 0.15f * c);
    }

    return finiteBounded(out.branch128)
        && finiteBounded(out.branch256A)
        && finiteBounded(out.branch256B)
        && finiteBounded(out.branch256C)
        && finiteBounded(out.feature452)
        && finiteBounded(out.feature506)
        && finiteBounded(out.latent512);
}

} // namespace Sonicraft::AIStrings
