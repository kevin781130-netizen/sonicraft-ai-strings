#pragma once
#include <filesystem>
#include <string>
namespace Sonicraft::InProcess {
struct PromotionPaths {std::filesystem::path renderer,decoder,ortRuntime;std::string promotionId;};
bool verifyPromotionLock(const std::filesystem::path& lock,PromotionPaths& out,std::string& reason);
}
