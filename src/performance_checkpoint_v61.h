#pragma once
#include <array>
#include <string_view>
namespace Sonicraft::AIStrings {
inline constexpr int kPerformanceCheckpointSchemaV61 = 1;
inline constexpr int kCheckpointEvidenceNamespaceCountV61 = 5;
inline constexpr int kCheckpointCompileArtifactCountV61 = 12;
inline constexpr bool checkpointEmbedsAudioV61() noexcept { return false; }
inline constexpr bool checkpointEmbedsMidiBytesV61() noexcept { return false; }
inline constexpr bool checkpointReplayMutatesLiveStateV61() noexcept { return false; }
inline constexpr bool checkpointRestoreIsExplicitV61() noexcept { return true; }
inline constexpr bool checkpointClaimsExactAudioReplayV61() noexcept { return false; }
inline constexpr std::array<std::string_view,5> kCheckpointEvidenceNamespacesV61 = {
    "utility_v55","audit_v56","similarity_v57","archetype_v58","mixture_v59"
};
} // namespace Sonicraft::AIStrings
