#pragma once

#include <algorithm>
#include <array>
#include <cstddef>

namespace Sonicraft::AIStrings {

enum class OrchestraInstrument : int {
    DoubleBass = 0,
    Cello,
    Viola,
    Violin,
    Piccolo,
    Flute,
    Oboe,
    ClarinetA,
    Bassoon,
    TenorSaxophone,
    AltoSaxophone,
    FrenchHorn,
    TrumpetBb,
    Tuba,
    Trombone,
    Count
};

struct OrchestraInstrumentDescriptor {
    OrchestraInstrument instrument;
    const char* role;
    const char* family;
    const char* nameEn;
    const char* nameZhUtf8;
};

inline constexpr std::array<OrchestraInstrumentDescriptor, 15> kOrchestraInstruments{{
    {OrchestraInstrument::DoubleBass, "double_bass", "strings", "Double Bass", "低音提琴"},
    {OrchestraInstrument::Cello, "cello", "strings", "Cello", "大提琴"},
    {OrchestraInstrument::Viola, "viola", "strings", "Viola", "中提琴"},
    {OrchestraInstrument::Violin, "violin", "strings", "Violin", "小提琴"},
    {OrchestraInstrument::Piccolo, "piccolo", "woodwind", "Piccolo", "短笛"},
    {OrchestraInstrument::Flute, "flute", "woodwind", "Flute", "長笛"},
    {OrchestraInstrument::Oboe, "oboe", "woodwind", "Oboe", "雙簧管"},
    {OrchestraInstrument::ClarinetA, "clarinet_a", "woodwind", "Clarinet in A", "A調單簧管"},
    {OrchestraInstrument::Bassoon, "bassoon", "woodwind", "Bassoon", "巴松管"},
    {OrchestraInstrument::TenorSaxophone, "tenor_saxophone", "woodwind", "Tenor Saxophone", "次中音薩克斯風"},
    {OrchestraInstrument::AltoSaxophone, "alto_saxophone", "woodwind", "Alto Saxophone", "中音薩克斯風"},
    {OrchestraInstrument::FrenchHorn, "french_horn", "brass", "French Horn", "圓號"},
    {OrchestraInstrument::TrumpetBb, "trumpet_bb", "brass", "B-flat Trumpet", "B♭調小號"},
    {OrchestraInstrument::Tuba, "tuba", "brass", "Tuba", "大號"},
    {OrchestraInstrument::Trombone, "trombone", "brass", "Trombone", "長號"},
}};

inline constexpr int kOrchestraInstrumentCount = static_cast<int>(kOrchestraInstruments.size());

inline int orchestraInstrumentIndexFromNormalized(float value) noexcept {
    const float v = std::clamp(value, 0.f, 1.f);
    return std::clamp(static_cast<int>(v * float(kOrchestraInstrumentCount - 1) + .5f),
                      0, kOrchestraInstrumentCount - 1);
}

inline float orchestraInstrumentNormalizedFromIndex(int index) noexcept {
    const int i = std::clamp(index, 0, kOrchestraInstrumentCount - 1);
    return float(i) / float(kOrchestraInstrumentCount - 1);
}

inline const OrchestraInstrumentDescriptor& orchestraInstrumentDescriptor(int index) noexcept {
    return kOrchestraInstruments[static_cast<std::size_t>(
        std::clamp(index, 0, kOrchestraInstrumentCount - 1))];
}

} // namespace Sonicraft::AIStrings
