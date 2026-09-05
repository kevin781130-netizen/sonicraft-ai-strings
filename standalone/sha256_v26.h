#pragma once
#include <array>
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
namespace Sonicraft::CryptoV26 {
std::array<uint8_t,32> sha256(std::span<const uint8_t> bytes);
std::string sha256Hex(std::span<const uint8_t> bytes);
std::string sha256FileHex(const std::filesystem::path& path);
}
