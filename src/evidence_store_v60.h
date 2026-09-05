#pragma once
#include <array>
#include <string_view>
namespace Sonicraft::AIStrings {
inline constexpr int kEvidenceStoreSchemaV60 = 1;
inline constexpr int kEvidenceNamespaceCountV60 = 5;
inline constexpr int kEvidenceMaxCommitsV60 = 32;
inline constexpr std::array<std::string_view,5> kEvidenceNamespacesV60 = {
    "utility_v55","audit_v56","similarity_v57","archetype_v58","mixture_v59"
};
inline constexpr bool evidenceStoreBlendsAlgorithmsV60() noexcept { return false; }
inline constexpr bool evidenceStoreIncludesRepairPolicyV49() noexcept { return false; }
inline constexpr bool evidenceStoreRequiresDOriginalChangeV60() noexcept { return false; }
} // namespace Sonicraft::AIStrings
