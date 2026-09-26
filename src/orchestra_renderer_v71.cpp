#include "orchestra_renderer_v71.h"

#include <algorithm>
#include <cmath>

namespace Sonicraft::AIStrings {
namespace {

constexpr double kTwoPi = 6.283185307179586476925286766559;

float clamp01(float v) noexcept {
    return std::clamp(std::isfinite(v) ? v : 0.f, 0.f, 1.f);
}

float instrumentPan(OrchestraInstrument instrument) noexcept {
    static constexpr float kPan[15] = {
        .18f, .12f, -.04f, -.22f,
        -.35f, -.28f, -.18f, -.08f, .10f,
        .18f, .12f, .25f, .32f, .36f, .28f
    };
    const int i = std::clamp(static_cast<int>(instrument), 0, 14);
    return kPan[i];
}

float familyBrightness(OrchestraInstrument instrument) noexcept {
    const int i = std::clamp(static_cast<int>(instrument), 0, 14);
    if (i <= 3) return .72f;          // strings
    if (i <= 10) return .88f;         // woodwinds / sax
    return .96f;                      // brass
}

float articulationRelease(std::uint32_t bits) noexcept {
    if (bits & kArtPizzicato) return .09f;
    if (bits & kArtStaccato) return .07f;
    if (bits & kArtMarcato) return .12f;
    return .28f;
}

float articulationAttack(std::uint32_t bits, float attackCharacter) noexcept {
    const float character = clamp01(attackCharacter);
    if (bits & kArtPizzicato) return .0015f;
    if (bits & kArtStaccato) return .0025f;
    if (bits & kArtMarcato) return .0035f;
    if (bits & kArtLegato) return .008f + .012f * (1.f - character);
    return .012f + .040f * (1.f - character);
}

float featureRms(const std::array<float, OrchestraConditioningFeatures::kLatent512>& x) noexcept {
    double sum = 0.0;
    for (float v : x) sum += double(v) * double(v);
    return static_cast<float>(std::sqrt(sum / double(x.size())));
}

} // namespace

void OrchestraRendererV71::reset(double sampleRate) noexcept {
    sampleRate_ = (std::isfinite(sampleRate) && sampleRate > 1000.0)
        ? sampleRate : 48000.0;
    voices_.fill(Voice{});
}

void OrchestraRendererV71::allNotesOff() noexcept {
    for (auto& v : voices_) {
        if (!v.active) continue;
        v.releasing = true;
    }
}

OrchestraRendererV71::Voice* OrchestraRendererV71::allocateVoice() noexcept {
    for (auto& v : voices_) if (!v.active) return &v;
    Voice* oldest = &voices_.front();
    for (auto& v : voices_)
        if (v.ageSeconds > oldest->ageSeconds) oldest = &v;
    return oldest;
}

double OrchestraRendererV71::midiToHz(float note) noexcept {
    return 440.0 * std::pow(2.0, (double(note) - 69.0) / 12.0);
}

bool OrchestraRendererV71::noteOn(
    int lane,
    int note,
    const MusicalControlFrame& control,
    const OrchestraPerformanceState& performance,
    const OrchestraConditioningFeatures& features) noexcept
{
    if (lane < 0 || lane >= 16 || note < 0 || note > 127) return false;

    auto* v = allocateVoice();
    *v = Voice{};
    v->active = true;
    v->lane = lane;
    v->note = note;
    v->instrument = performance.instrument;
    v->articulationBits = control.articulationBits;
    v->velocity = clamp01(control.velocity);
    v->dynamics = clamp01(control.dynamics);
    v->expression = clamp01(control.expression);
    v->vibrato = clamp01(control.vibrato);
    v->attackCharacter = clamp01(control.attackCharacter);
    v->transition = clamp01(control.transition);
    v->pan = instrumentPan(performance.instrument);
    v->featureEnergy = featureRms(features.latent512);

    const float pitch = std::clamp(
        std::isfinite(control.midiPitch) ? control.midiPitch : float(note),
        0.f, 127.f);
    const float cents = std::clamp(
        std::isfinite(control.pitchCents) ? control.pitchCents : 0.f,
        -200.f, 200.f);
    v->baseFrequency = midiToHz(pitch + cents / 100.f);

    const float bright = familyBrightness(performance.instrument);
    float gainSum = 0.f;
    for (int h = 0; h < kHarmonics; ++h) {
        const float order = float(h + 1);
        const float latent = features.latent512[(h * 29 + 7) & 511];
        const float branch = features.branch256A[(h * 17 + 3) & 255];
        const float tilt = std::pow(order, -(.78f + .52f * (1.f - bright)));
        const float modulation = std::clamp(
            1.f + .34f * latent + .18f * branch,
            .18f, 1.82f);
        float g = tilt * modulation;
        if ((control.articulationBits & kArtHarmonic) && h != 1 && h != 3)
            g *= .32f;
        if (control.articulationBits & kArtMute)
            g *= 1.f / (1.f + .10f * order);
        v->harmonicGain[h] = g;
        gainSum += g;
        v->harmonicPhase[h] =
            double(features.branch128[(h * 7 + 5) & 127]) * 0.18;
    }
    if (!(gainSum > 1e-6f) || !std::isfinite(gainSum)) {
        v->active = false;
        return false;
    }
    const float norm = 1.f / gainSum;
    for (auto& g : v->harmonicGain) g *= norm * float(kHarmonics) * .85f;
    return true;
}

void OrchestraRendererV71::noteOff(int lane, int note) noexcept {
    for (auto& v : voices_) {
        if (v.active && v.lane == lane && v.note == note)
            v.releasing = true;
    }
}

void OrchestraRendererV71::render(
    float* left, float* right, std::int32_t samples, float mix) noexcept
{
    if (!left || !right || samples <= 0) return;
    const float wet = clamp01(mix);
    if (wet <= 0.f) return;

    for (std::int32_t i = 0; i < samples; ++i) {
        float l = 0.f, r = 0.f;
        for (auto& v : voices_) {
            if (!v.active) continue;

            v.ageSeconds += 1.0 / sampleRate_;
            const double attack = std::max(
                0.0005,
                double(articulationAttack(v.articulationBits, v.attackCharacter)));
            const double release = std::max(
                0.008,
                double(articulationRelease(v.articulationBits)));
            const double target = v.releasing ? 0.0 : 1.0;
            const double tau = v.releasing ? release : attack;
            const double coeff = 1.0 - std::exp(-1.0 / (sampleRate_ * tau));
            v.envelope += (target - v.envelope) * coeff;

            if (v.releasing && v.envelope < 1e-5) {
                v.active = false;
                continue;
            }

            const double vibRate =
                4.7 + 1.7 * double(v.vibrato)
                + 0.22 * double(v.transition);
            const double vibDepthCents =
                (v.articulationBits & (kArtStaccato | kArtPizzicato))
                ? 2.5 * double(v.vibrato)
                : 30.0 * double(v.vibrato);
            v.vibratoPhase += kTwoPi * vibRate / sampleRate_;
            if (v.vibratoPhase > kTwoPi) v.vibratoPhase -= kTwoPi;

            const double cents =
                vibDepthCents * std::sin(v.vibratoPhase)
                * std::min(1.0, v.ageSeconds / 0.18);
            const double f0 =
                v.baseFrequency * std::pow(2.0, cents / 1200.0);
            v.phase += kTwoPi * f0 / sampleRate_;
            if (v.phase > kTwoPi) v.phase -= kTwoPi;

            double s = 0.0;
            for (int h = 0; h < kHarmonics; ++h) {
                const int order = h + 1;
                const double freq = f0 * double(order);
                if (freq >= sampleRate_ * 0.47) break;
                s += double(v.harmonicGain[h])
                    * std::sin(double(order) * v.phase + v.harmonicPhase[h]);
            }
            s /= double(kHarmonics);

            if (v.articulationBits & kArtTremolo) {
                const double trem = .72 + .28 * std::sin(
                    kTwoPi * 8.7 * v.ageSeconds);
                s *= trem;
            }

            const float gain =
                wet * .30f
                * v.velocity
                * (.18f + .82f * v.dynamics)
                * v.expression
                * float(v.envelope)
                * (0.82f + 0.18f * std::clamp(v.featureEnergy, 0.f, 1.f));

            const float sample = float(std::tanh(s * double(gain) * 1.25));
            const float pan = std::clamp(v.pan, -.95f, .95f);
            const float gl = std::sqrt(.5f * (1.f - pan));
            const float gr = std::sqrt(.5f * (1.f + pan));
            l += sample * gl;
            r += sample * gr;
        }

        left[i] += std::clamp(l, -1.f, 1.f);
        right[i] += std::clamp(r, -1.f, 1.f);
    }
}

int OrchestraRendererV71::activeVoiceCount() const noexcept {
    int n = 0;
    for (const auto& v : voices_) if (v.active) ++n;
    return n;
}

} // namespace Sonicraft::AIStrings
