#pragma once

#include <algorithm>
#include <cstdint>

namespace Sonicraft::AIStrings {

// Observed across the current 15 confirmed DNNI v4 sources.
// These are byte-layout facts/hypotheses only, not proprietary tensor semantics.
struct DnniObservedRuntimeLayout {
    static constexpr std::uint64_t kSharedCoreBytes = 126227640ull;
    static constexpr std::uint64_t kVariableGroupBytes = 784352ull;
    static constexpr std::uint64_t kTailSubblockBytes = 196088ull;
    static constexpr std::uint64_t kCommonZeroGapOffset = 97434392ull;
    static constexpr std::uint64_t kCommonZeroGapBytes = 1536ull;
    static constexpr int kSubblocksPerCandidateGroup = 4;

    bool compatible {false};
    bool currentFamilyObserved {false};
    std::uint64_t weightsBytes {0};
    std::uint64_t variableTailBytes {0};
    int candidateGroupCount {0};
    int tailSubblockCount {0};
};

inline DnniObservedRuntimeLayout analyzeDnniObservedRuntimeLayout(std::uint64_t weightsBytes) noexcept {
    DnniObservedRuntimeLayout out{};
    out.weightsBytes = weightsBytes;
    if (weightsBytes < DnniObservedRuntimeLayout::kSharedCoreBytes) return out;

    out.variableTailBytes = weightsBytes - DnniObservedRuntimeLayout::kSharedCoreBytes;
    if (out.variableTailBytes % DnniObservedRuntimeLayout::kVariableGroupBytes != 0) return out;
    if (out.variableTailBytes % DnniObservedRuntimeLayout::kTailSubblockBytes != 0) return out;

    out.candidateGroupCount = static_cast<int>(
        out.variableTailBytes / DnniObservedRuntimeLayout::kVariableGroupBytes);
    out.tailSubblockCount = static_cast<int>(
        out.variableTailBytes / DnniObservedRuntimeLayout::kTailSubblockBytes);
    out.compatible =
        out.tailSubblockCount ==
        out.candidateGroupCount * DnniObservedRuntimeLayout::kSubblocksPerCandidateGroup;

    // Current confirmed sources use 8, 9 or 11 groups. Keep "compatible" separate
    // so a future 10-group source can be inspected without silently claiming it was observed.
    out.currentFamilyObserved =
        out.compatible &&
        (out.candidateGroupCount == 8 ||
         out.candidateGroupCount == 9 ||
         out.candidateGroupCount == 11);
    return out;
}

} // namespace Sonicraft::AIStrings
