#pragma once
#include <cstdint>

namespace Sonicraft::AIStrings {

enum class Articulation : int32_t {
    Sustain = 0,
    Legato = 1,
    Portamento = 2,
    ExpressiveLong = 3,
    Marcato = 4,
    Staccato = 5,
    Spiccato = 6,
    Tremolo = 7,
    Pizzicato = 8,
    Trill = 9,
    Harmonic = 10,
    Flautando = 11,
};

static constexpr int kArticulationCount = 12;
static constexpr int kKeyswitchBaseMidi = 24; // C0 when Cubase middle-C preference is C3.

inline bool isKeyswitch(int midiNote) {
    return midiNote >= kKeyswitchBaseMidi && midiNote < (kKeyswitchBaseMidi + kArticulationCount);
}
inline int articulationFromKeyswitch(int midiNote) { return midiNote - kKeyswitchBaseMidi; }

} // namespace Sonicraft::AIStrings
