#pragma once
#include "host_cycle_scope_v31.h"
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace Sonicraft::AIStrings {

enum TakeCarouselMode : int {
    kTakeCarouselOff = 0,
    kTakeCarouselManual = 1,
    kTakeCarouselAutoLoop = 2,
};

inline int takeIndexFromNormalized(float v) noexcept {
    return std::clamp(static_cast<int>(std::clamp(v,0.f,1.f) * 3.f + .5f), 0, 3);
}

inline float deriveTakeNonce(float baseNonce, int takeIndex) noexcept {
    const float base = std::clamp(baseNonce, 0.f, 1.f);
    const int idx = std::clamp(takeIndex, 0, 3);
    if (idx == 0) return base; // Take A is exactly the user's base Retake Seed.
    const std::uint32_t q = static_cast<std::uint32_t>(std::llround(static_cast<double>(base) * 16777215.0));
    std::uint32_t x = q ^ (0x9E3779B9u * static_cast<std::uint32_t>(idx + 1));
    x ^= x >> 16; x *= 0x7FEB352Du; x ^= x >> 15; x *= 0x846CA68Bu; x ^= x >> 16;
    return static_cast<float>(x & 0x00FFFFFFu) / 16777215.f;
}

inline bool sameCycleWindow(const HostCycleWindow& a, const HostCycleWindow& b) noexcept {
    return a.valid && b.valid && std::abs(a.startQuarter-b.startQuarter) < 1e-7 &&
           std::abs(a.endQuarter-b.endQuarter) < 1e-7;
}

inline bool detectCycleWrap(double previousQuarter, double currentQuarter,
                            const HostCycleWindow& previousWindow,
                            const HostCycleWindow& currentWindow) noexcept {
    if (!std::isfinite(previousQuarter) || !std::isfinite(currentQuarter) ||
        !sameCycleWindow(previousWindow, currentWindow)) return false;
    const double length = currentWindow.endQuarter - currentWindow.startQuarter;
    if (!(length > 0.0)) return false;
    // Require a substantial backwards jump inside the same locator range. This rejects ordinary
    // small host timing jitter and seeks while still catching a normal cycle wrap.
    return previousQuarter >= currentWindow.startQuarter && previousQuarter <= currentWindow.endQuarter + 1e-7 &&
           currentQuarter >= currentWindow.startQuarter - 1e-7 && currentQuarter < currentWindow.endQuarter &&
           (previousQuarter - currentQuarter) > length * 0.45;
}

class RetakeCarouselTracker {
public:
    int update(int mode, int selectedTake, bool frozen, bool playing,
               bool quarterValid, double currentQuarter, const HostCycleWindow& window) noexcept {
        selectedTake = std::clamp(selectedTake,0,3);
        mode = std::clamp(mode,0,2);

        if (mode == kTakeCarouselOff || !playing) {
            activeTake_ = selectedTake;
        } else if (!wasPlaying_) {
            // Every fresh transport start is reproducible from the explicitly selected take.
            activeTake_ = selectedTake;
        } else if (mode == kTakeCarouselManual) {
            activeTake_ = selectedTake;
        } else if (mode == kTakeCarouselAutoLoop && !frozen && quarterValid && lastQuarterValid_ &&
                   detectCycleWrap(lastQuarter_, currentQuarter, lastWindow_, window)) {
            activeTake_ = (activeTake_ + 1) & 3;
        }

        wasPlaying_ = playing;
        if (playing && quarterValid && window.valid) {
            lastQuarterValid_ = true;
            lastQuarter_ = currentQuarter;
            lastWindow_ = window;
        } else {
            lastQuarterValid_ = false;
            lastWindow_ = {};
        }
        lastMode_ = mode;
        return activeTake_;
    }

    int activeTake() const noexcept { return activeTake_; }
    void reset(int selectedTake=0) noexcept {
        activeTake_ = std::clamp(selectedTake,0,3);
        wasPlaying_ = false;
        lastQuarterValid_ = false;
        lastQuarter_ = 0.0;
        lastWindow_ = {};
        lastMode_ = kTakeCarouselOff;
    }
private:
    int activeTake_ {0};
    int lastMode_ {kTakeCarouselOff};
    bool wasPlaying_ {false};
    bool lastQuarterValid_ {false};
    double lastQuarter_ {0.0};
    HostCycleWindow lastWindow_ {};
};

inline float resolveCarouselNonce(int carouselMode, bool scopeRetakeEnabled, bool insideScope,
                                  float baseNonce, int manualTake, int autoTake) noexcept {
    if (carouselMode == kTakeCarouselOff || !scopeRetakeEnabled || !insideScope) return baseNonce;
    const int idx = carouselMode == kTakeCarouselManual ? std::clamp(manualTake,0,3) : std::clamp(autoTake,0,3);
    return deriveTakeNonce(baseNonce, idx);
}

} // namespace Sonicraft::AIStrings
