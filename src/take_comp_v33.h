#pragma once
#include "retake_carousel_v32.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace Sonicraft::AIStrings {

enum TakeCompMode : int {
    kTakeCompOff = 0,
    kTakeCompPhrase = 1,
};

struct TakeCompEntry {
    std::int64_t phraseKey {0};
    std::uint8_t takeIndex {0};
    bool valid {false};
};

inline std::int64_t phraseKeyFromQuarter(double quarter, double phraseLengthQuarter) noexcept {
    const double len = std::max(0.25, phraseLengthQuarter);
    if (!std::isfinite(quarter)) return 0;
    return static_cast<std::int64_t>(std::floor((quarter + 1e-9) / len));
}

class PhraseTakeComp {
public:
    static constexpr int kCapacity = 128;

    void clear() noexcept {
        for (auto& e : entries_) e = {};
        stamp_ = 1;
    }

    bool commit(std::int64_t phraseKey, int takeIndex) noexcept {
        takeIndex = std::clamp(takeIndex, 0, 3);
        for (auto& e : entries_) {
            if (e.valid && e.phraseKey == phraseKey) {
                e.takeIndex = static_cast<std::uint8_t>(takeIndex);
                return true;
            }
        }
        for (auto& e : entries_) {
            if (!e.valid) {
                e = {phraseKey, static_cast<std::uint8_t>(takeIndex), true};
                return true;
            }
        }
        // Fixed-size realtime-safe table: deterministic replacement, no heap allocation.
        auto& e = entries_[static_cast<std::size_t>(stamp_++ % kCapacity)];
        e = {phraseKey, static_cast<std::uint8_t>(takeIndex), true};
        return true;
    }

    bool lookup(std::int64_t phraseKey, int& takeIndex) const noexcept {
        for (const auto& e : entries_) {
            if (e.valid && e.phraseKey == phraseKey) {
                takeIndex = static_cast<int>(e.takeIndex);
                return true;
            }
        }
        return false;
    }

    int committedCount() const noexcept {
        int n=0; for (const auto& e : entries_) if (e.valid) ++n; return n;
    }

private:
    std::array<TakeCompEntry,kCapacity> entries_ {};
    std::uint32_t stamp_ {1};
};

inline int resolveCompTake(const PhraseTakeComp& comp, int compMode, bool insideScope,
                           double quarter, double phraseLengthQuarter, int fallbackTake) noexcept {
    if (compMode != kTakeCompPhrase || !insideScope) return std::clamp(fallbackTake,0,3);
    int take = fallbackTake;
    if (comp.lookup(phraseKeyFromQuarter(quarter, phraseLengthQuarter), take)) return take;
    return std::clamp(fallbackTake,0,3);
}

} // namespace Sonicraft::AIStrings
