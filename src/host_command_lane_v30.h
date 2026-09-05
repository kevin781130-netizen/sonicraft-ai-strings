#pragma once

namespace Sonicraft::AIStrings {
// MIDI CC 102..119 are undefined/reserved controller numbers. SONICRAFT uses them only as
// global host-intelligence commands. Conventional musical CC lanes remain untouched.
enum HostCommandCC : int {
    kCC_AIAssist = 102,
    kCC_PerformanceStyle = 103,
    kCC_SmartDynamics = 104,
    kCC_SmartArticulation = 105,
    kCC_RetakeTarget = 106,
    kCC_RetakeAmount = 107,
    kCC_RetakeSeed = 108,
    kCC_MidiAuthorityLock = 109,
    kCC_PhraseDirector = 110,
    kCC_EnsembleLooseness = 111,
    kCC_AutoDivisi = 112,
    kCC_StagePerspective = 113,
    kCC_IndependentPolyphony = 114,
    kCC_AIMix = 115,
    kCC_AILookAhead = 116,
    kCC_LayoutMode = 117,
    kCC_SingleInstrument = 118,
    kCC_Humanize = 119,
};
static constexpr int kHostCommandCCFirst = kCC_AIAssist;
static constexpr int kHostCommandCCLast = kCC_Humanize;
static_assert(kHostCommandCCLast-kHostCommandCCFirst+1 == 18, "Host command lane must remain contiguous");
}
