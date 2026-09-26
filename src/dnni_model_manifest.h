#pragma once

#include "orchestra_instruments.h"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <string>
#include <string_view>
#include <vector>

namespace Sonicraft::AIStrings {

struct DnniNativeModelRef {
    bool present {false};
    bool headerVerified {false};
    int instrumentIndex {-1};
    std::string role;
    std::string family;
    std::string labelEn;
    std::string labelZhUtf8;
    std::string sourceUuid;
    std::filesystem::path path;
    std::uint64_t fileSize {0};
    std::string sourceSha256;
    std::uint64_t weightsOffset {0};
    std::uint64_t weightsBytes {0};
    std::string weightsSha256;
};

class DnniModelManifestCatalog {
public:
    static constexpr const char* kMagic = "SONICRAFT_DNNI_CATALOG_V1";

    bool load(const std::filesystem::path& manifest) {
        for (auto& m : models_) m = {};
        loadedPath_.clear();

        std::ifstream f(manifest, std::ios::binary);
        if (!f) return false;

        std::string line;
        if (!std::getline(f, line) || trimCr(line) != kMagic) return false;

        while (std::getline(f, line)) {
            trimCr(line);
            if (line.empty()) continue;
            const auto fields = split(line, '|');
            if (fields.size() != 12) return false;

            int index = -1;
            std::uint64_t fileSize = 0, weightsOffset = 0, weightsBytes = 0;
            try {
                index = std::stoi(fields[0]);
                fileSize = static_cast<std::uint64_t>(std::stoull(fields[7]));
                weightsOffset = static_cast<std::uint64_t>(std::stoull(fields[9]));
                weightsBytes = static_cast<std::uint64_t>(std::stoull(fields[10]));
            } catch (...) {
                return false;
            }
            if (index < 0 || index >= kOrchestraInstrumentCount) return false;
            if (models_[static_cast<std::size_t>(index)].present) return false;

            auto& m = models_[static_cast<std::size_t>(index)];
            m.present = true;
            m.instrumentIndex = index;
            m.role = fields[1];
            m.family = fields[2];
            m.labelEn = fields[3];
            m.labelZhUtf8 = fields[4];
            m.sourceUuid = fields[5];
            m.path = std::filesystem::u8path(fields[6]);
            m.fileSize = fileSize;
            m.sourceSha256 = fields[8];
            m.weightsOffset = weightsOffset;
            m.weightsBytes = weightsBytes;
            m.weightsSha256 = fields[11];
            m.headerVerified = verifyHeader(m);
        }

        loadedPath_ = manifest;
        return true;
    }

    const DnniNativeModelRef* model(int instrumentIndex) const noexcept {
        if (instrumentIndex < 0 || instrumentIndex >= kOrchestraInstrumentCount) return nullptr;
        const auto& m = models_[static_cast<std::size_t>(instrumentIndex)];
        return m.present ? &m : nullptr;
    }

    bool ready(int instrumentIndex) const noexcept {
        const auto* m = model(instrumentIndex);
        return m && m->headerVerified;
    }

    int presentCount() const noexcept {
        int n = 0;
        for (const auto& m : models_) if (m.present && m.headerVerified) ++n;
        return n;
    }

    const std::filesystem::path& loadedPath() const noexcept { return loadedPath_; }

private:
    std::array<DnniNativeModelRef, kOrchestraInstrumentCount> models_{};
    std::filesystem::path loadedPath_{};

    static void trimCr(std::string& s) {
        if (!s.empty() && s.back() == '\r') s.pop_back();
    }

    static std::vector<std::string> split(const std::string& s, char delim) {
        std::vector<std::string> out;
        std::size_t start = 0;
        while (true) {
            const auto pos = s.find(delim, start);
            if (pos == std::string::npos) {
                out.push_back(s.substr(start));
                break;
            }
            out.push_back(s.substr(start, pos - start));
            start = pos + 1;
        }
        return out;
    }

    static std::uint32_t readU32Le(const unsigned char* p) noexcept {
        return std::uint32_t(p[0]) |
               (std::uint32_t(p[1]) << 8) |
               (std::uint32_t(p[2]) << 16) |
               (std::uint32_t(p[3]) << 24);
    }

    static std::uint64_t readU64Le(const unsigned char* p) noexcept {
        std::uint64_t v = 0;
        for (int i = 7; i >= 0; --i) v = (v << 8) | p[i];
        return v;
    }

    static bool verifyHeader(const DnniNativeModelRef& m) {
        std::error_code ec;
        if (!std::filesystem::exists(m.path, ec) || ec) return false;
        const auto size = std::filesystem::file_size(m.path, ec);
        if (ec || size != m.fileSize) return false;

        std::ifstream f(m.path, std::ios::binary);
        if (!f) return false;
        std::array<unsigned char, 140> h{};
        f.read(reinterpret_cast<char*>(h.data()), static_cast<std::streamsize>(h.size()));
        if (f.gcount() != static_cast<std::streamsize>(h.size())) return false;
        if (h[0] != 0xff || h[1] != 0x00 || h[2] != 0xca || h[3] != 0x7f) return false;
        if (readU32Le(h.data() + 4) != 4u || readU32Le(h.data() + 8) != 140u) return false;

        const std::uint64_t weightsOffset = readU64Le(h.data() + 80);
        const std::uint64_t weightsBytes = readU64Le(h.data() + 88);
        if (weightsOffset != m.weightsOffset || weightsBytes != m.weightsBytes) return false;
        if (weightsOffset + weightsBytes > m.fileSize) return false;
        return true;
    }
};

inline std::filesystem::path defaultDnniCatalogPath() {
    if (const char* p = std::getenv("SONICRAFT_DNNI_CATALOG"); p && *p)
        return std::filesystem::u8path(p);
    if (const char* p = std::getenv("SONICRAFT_DNNI_DIR"); p && *p)
        return std::filesystem::u8path(p) / "sonicraft_dnni_catalog.txt";
#ifdef _WIN32
    if (const char* p = std::getenv("LOCALAPPDATA"); p && *p)
        return std::filesystem::u8path(p) / "SONICRAFT" / "models" / "dnni" / "sonicraft_dnni_catalog.txt";
#endif
    std::error_code ec;
    const auto cwd = std::filesystem::current_path(ec);
    return ec ? std::filesystem::path("models/dnni/sonicraft_dnni_catalog.txt")
              : cwd / "models" / "dnni" / "sonicraft_dnni_catalog.txt";
}

} // namespace Sonicraft::AIStrings
