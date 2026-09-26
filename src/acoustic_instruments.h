#pragma once
#include <array>
#include <algorithm>
namespace Sonicraft::AIStrings {
// Independent synthesis previews. IDs are SONICRAFT-owned and contain no third-party assets.
struct AcousticProfile { const char* name; float brightness,air,bodyHz,bodyMix,attack,release; bool bowed; };
inline constexpr std::array<AcousticProfile,15> kAcousticProfiles{{
    {"Violin",1.00f,.095f,680.f,.30f,.020f,.22f,true},
    {"Viola",.82f,.085f,530.f,.34f,.027f,.27f,true},
    {"Cello",.68f,.077f,320.f,.39f,.032f,.32f,true},
    {"Contrabass",.54f,.068f,195.f,.44f,.043f,.40f,true},
    {"Piccolo",1.22f,.052f,2200.f,.12f,.018f,.12f,false},
    {"Flute",.58f,.110f,1250.f,.16f,.035f,.18f,false},
    {"Oboe",1.18f,.075f,1100.f,.26f,.038f,.20f,false},
    {"Clarinet (A)",.55f,.075f,750.f,.24f,.025f,.16f,false},
    {"Bassoon",.78f,.062f,430.f,.29f,.042f,.23f,false},
    {"French Horn",.67f,.055f,470.f,.34f,.048f,.26f,false},
    {"Trumpet (Bb)",1.25f,.055f,1450.f,.30f,.016f,.15f,false},
    {"Trombone",.90f,.050f,650.f,.31f,.033f,.21f,false},
    {"Tuba",.48f,.040f,285.f,.38f,.047f,.28f,false},
    {"Alto Saxophone",.96f,.095f,900.f,.28f,.024f,.19f,false},
    {"Tenor Saxophone",.80f,.085f,620.f,.31f,.029f,.22f,false}
}};
inline constexpr int acousticProfileIndex(int index) noexcept { return std::clamp(index,0,14); }
// 0 retains all existing Q4 behavior. 1..15 select preview profiles.
inline constexpr int acousticOverrideIndex(float normalized) noexcept {
    const int slot=std::clamp(int(normalized*15.f+.5f),0,15);
    return slot==0?-1:slot-1;
}
}
