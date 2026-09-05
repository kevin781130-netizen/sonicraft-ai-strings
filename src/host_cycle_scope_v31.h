#pragma once
#include <algorithm>
#include <cmath>

namespace Sonicraft::AIStrings {

// v3.1 Host Scope uses the musical locator/cycle range already supplied by the VST3 host.
// No host-specific private API is required.
enum HostScopeMode : int {
    kHostScopeOff = 0,
    kHostScopeRetake = 1,
    kHostScopeDirector = 2,
    kHostScopeBoth = 3,
};

struct HostCycleWindow {
    bool valid {false};
    double startQuarter {0.0};
    double endQuarter {0.0};
};

struct ScopedPerformanceState {
    float performanceStyle {0.f};
    float retakeTarget {0.f};
    float retakeAmount {0.f};
    float retakeNonce {0.f};
    float phraseDirector {1.f};
    float ensembleLooseness {.18f};
};

inline bool hostScopeIncludesRetake(int mode) noexcept {
    return mode == kHostScopeRetake || mode == kHostScopeBoth;
}
inline bool hostScopeIncludesDirector(int mode) noexcept {
    return mode == kHostScopeDirector || mode == kHostScopeBoth;
}
inline bool hostScopeInside(double quarter, const HostCycleWindow& w) noexcept {
    return w.valid && std::isfinite(quarter) && std::isfinite(w.startQuarter) &&
           std::isfinite(w.endQuarter) && w.endQuarter > w.startQuarter &&
           quarter >= w.startQuarter && quarter < w.endQuarter;
}

// Retake is intentionally zero outside the locator range when scoped. Director preserves the
// user's global director state outside the locator range, and applies explicit v3.1 overrides inside.
inline ScopedPerformanceState resolveHostScope(
    int mode, bool inside,
    float baseStyle, float baseRetakeTarget, float baseRetakeAmount, float baseRetakeNonce,
    float basePhraseDirector, float baseLooseness,
    float scopeStyle, float scopeLooseness) noexcept {
    ScopedPerformanceState s{baseStyle,baseRetakeTarget,baseRetakeAmount,baseRetakeNonce,basePhraseDirector,baseLooseness};
    if (mode == kHostScopeOff) return s;
    if (hostScopeIncludesRetake(mode) && !inside) {
        s.retakeTarget = 0.f;
        s.retakeAmount = 0.f;
    }
    if (hostScopeIncludesDirector(mode) && inside) {
        s.performanceStyle = std::clamp(scopeStyle,0.f,1.f);
        s.phraseDirector = 1.f;
        s.ensembleLooseness = std::clamp(scopeLooseness,0.f,1.f);
    }
    return s;
}

inline int boundarySampleOffset(double blockStartQuarter, double boundaryQuarter,
                                double tempoBpm, double sampleRate, int numSamples) noexcept {
    if (!std::isfinite(blockStartQuarter) || !std::isfinite(boundaryQuarter) ||
        !(tempoBpm > 0.0) || !(sampleRate > 0.0) || numSamples <= 0) return -1;
    const double deltaQuarter = boundaryQuarter - blockStartQuarter;
    const double samples = deltaQuarter * (60.0 / tempoBpm) * sampleRate;
    const long long rounded = std::llround(samples);
    if (rounded <= 0 || rounded >= numSamples) return -1;
    return static_cast<int>(rounded);
}

} // namespace Sonicraft::AIStrings
