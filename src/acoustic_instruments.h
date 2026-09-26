#pragma once
#include <array>
#include <algorithm>
namespace Sonicraft::AIStrings {
// Independent synthesis previews. IDs are SONICRAFT-owned and contain no third-party assets.
enum class AcousticFamily { Bowed, Flute, Reed, Brass, Sax };
struct AcousticProfile {
    const char* name;
    float brightness,air,bodyHz,bodyMix,attack,release;
    bool bowed;
    AcousticFamily family;
    float secondBodyHz,secondBodyMix;
};
inline constexpr std::array<AcousticProfile,15> kAcousticProfiles{{
    {"Violin",1.00f,.095f,680.f,.30f,.020f,.22f,true,AcousticFamily::Bowed,2800.f,.12f},
    {"Viola",.82f,.085f,530.f,.34f,.027f,.27f,true,AcousticFamily::Bowed,2100.f,.14f},
    {"Cello",.68f,.077f,320.f,.39f,.032f,.32f,true,AcousticFamily::Bowed,1250.f,.16f},
    {"Contrabass",.54f,.068f,195.f,.44f,.043f,.40f,true,AcousticFamily::Bowed,780.f,.18f},
    {"Piccolo",1.22f,.052f,2200.f,.12f,.018f,.12f,false,AcousticFamily::Flute,3700.f,.06f},
    {"Flute",.58f,.110f,1250.f,.16f,.035f,.18f,false,AcousticFamily::Flute,2400.f,.08f},
    {"Oboe",1.18f,.075f,1100.f,.26f,.038f,.20f,false,AcousticFamily::Reed,2650.f,.15f},
    {"Clarinet (A)",.55f,.075f,750.f,.24f,.025f,.16f,false,AcousticFamily::Reed,1700.f,.13f},
    {"Bassoon",.78f,.062f,430.f,.29f,.042f,.23f,false,AcousticFamily::Reed,1150.f,.18f},
    {"French Horn",.67f,.055f,470.f,.34f,.048f,.26f,false,AcousticFamily::Brass,1250.f,.15f},
    {"Trumpet (Bb)",1.25f,.055f,1450.f,.30f,.016f,.15f,false,AcousticFamily::Brass,3150.f,.15f},
    {"Trombone",.90f,.050f,650.f,.31f,.033f,.21f,false,AcousticFamily::Brass,1850.f,.16f},
    {"Tuba",.48f,.040f,285.f,.38f,.047f,.28f,false,AcousticFamily::Brass,930.f,.18f},
    {"Alto Saxophone",.96f,.095f,900.f,.28f,.024f,.19f,false,AcousticFamily::Sax,2250.f,.18f},
    {"Tenor Saxophone",.80f,.085f,620.f,.31f,.029f,.22f,false,AcousticFamily::Sax,1500.f,.19f}
}};
inline constexpr int acousticProfileIndex(int index) noexcept { return std::clamp(index,0,14); }
// 0 retains all existing Q4 behavior. 1..15 select preview profiles.
inline constexpr int acousticOverrideIndex(float normalized) noexcept {
    const int slot=std::clamp(int(normalized*15.f+.5f),0,15);
    return slot==0?-1:slot-1;
}
}
