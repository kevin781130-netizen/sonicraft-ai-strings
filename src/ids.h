#pragma once
#include "pluginterfaces/base/funknown.h"
#include "pluginterfaces/vst/vsttypes.h"

namespace Sonicraft::AIStrings {
static const Steinberg::FUID kProcessorUID(0xA842F139, 0x734C4D84, 0xB4C41984, 0x0C5E2181);
static const Steinberg::FUID kControllerUID(0xD8938D4A, 0xB47A4EA3, 0xA8D4505E, 0x0D89F711);
static constexpr int kPartCount = 4;

#include "host_command_lane_v30.h"

enum ParamID : Steinberg::Vst::ParamID {
    kParamMode = 100, kParamActivePart = 101, kParamHumanize = 102, kParamAIMix = 103,
    kParamLayoutMode = 104, kParamSingleInstrument = 105, kParamAIAssist = 106,
    kParamLookAhead = 107, kParamAutoDivisi = 108,
    kParamPerformanceStyle = 109, kParamSmartDynamics = 110, kParamSmartArticulation = 111,
    kParamRetakeTarget = 112, kParamRetakeAmount = 113, kParamRetakeNonce = 114,
    kParamStagePerspective = 115, kParamPolyphony = 116,
    kParamMidiAuthorityLock = 117, kParamPhraseDirector = 118, kParamEnsembleLooseness = 119,
    // v3.1 host-native locator/cycle scope. These are plugin automation parameters, not MIDI CCs;
    // CC 120..127 are MIDI channel-mode messages and are deliberately left untouched.
    kParamHostScopeMode = 120, kParamHostScopeStyle = 121, kParamHostScopeLooseness = 122,
    // v3.2 deterministic A/B/C/D locator Retake bank. These are VST parameters, not MIDI CC numbers.
    kParamTakeCarouselMode = 123, kParamTakeCarouselSelect = 124, kParamTakeCarouselFreeze = 125,
    // v3.3 phrase-level take comp. VST automation parameters; no MIDI channel-mode CCs are consumed.
    kParamTakeCompMode = 126, kParamTakeCompCommit = 127, kParamTakeCompClear = 128, kParamTakeCompPhraseLength = 129,
    // v3.4 persistent comp actions / review metadata. VST params only; MIDI CC map remains unchanged.
    kParamTakeCompUndo = 130, kParamTakeCompRedo = 131, kParamTakeCompFavorite = 132,
    kParamTakeCompReject = 133, kParamTakeCompCommitAll = 134,
    // v3.5 Performance Memory browser. 135..143 are controls; 144..148 are processor status outputs.
    kParamMemoryFollowPlayhead = 135, kParamMemoryPrev = 136, kParamMemoryNext = 137,
    kParamMemoryNextUnresolved = 138, kParamMemoryRecallTake = 139, kParamMemoryRecallApply = 140,
    kParamMemoryCommitRecall = 141, kParamMemoryFavoriteRecall = 142, kParamMemoryRejectRecall = 143,
    kParamMemoryCommittedTake = 144, kParamMemoryRecallFavorite = 145, kParamMemoryRecallRejected = 146,
    kParamMemoryCoverage = 147, kParamMemoryCursorPosition = 148, kParamMemoryClearPhrase = 149,
    // v3.6 Smart Comp Timeline: 8 committed-status slots + 8 smart-pick slots.
    kParamTimelineCommittedBase = 150, // 150..157
    kParamTimelineSmartPickBase = 158, // 158..165
    kParamSmartRankMode = 166, kParamSmartAudition = 167, kParamSmartCommit = 168,
    kParamSmartScore = 169, kParamTimelineCursorSlot = 170,
    kParamCommitUniqueFavorites = 171, kParamAutoCompUnresolved = 172,
    kParamSmartVariation = 173, kParamTimelineUnresolved = 174,
    // v3.7 audio-aware Take Judge. Read-only metrics stay below the legacy part-param range.
    kParamJudgeTrigger = 175, kParamJudgeWinner = 176,
    kParamJudgeOverallBase = 177,    // 177..180 A-D
    kParamJudgeDynamicsBase = 181,   // 181..184 A-D
    kParamJudgeAttackBase = 185,     // 185..188 A-D
    kParamJudgeTransitionBase = 189, // 189..192 A-D
    kParamJudgeStabilityBase = 193,  // 193..196 A-D
    kParamJudgeWinnerSafety = 197,
    kParamJudgeAuditionWinner = 198, kParamJudgeCommitWinner = 199,
    kParamPartDynamicsBase   = 200, // CC1
    kParamPartVibratoBase    = 210, // CC3; four active depth anchors + straight
    kParamPartExpressionBase = 220, // CC11
    kParamPartVolumeBase     = 230, // CC7
    kParamPartPanBase        = 240, // CC10
    kParamPartSustainBase    = 250, // CC64
    kParamPartLegatoBase     = 260, // CC68
    kParamPartRoomBase       = 270, // CC91
    kParamPartPitchBendBase  = 280,
    kParamPartArticulationBase = 290,
    kParamPartTransitionSpeedBase = 300,
    kParamPartShortTightnessBase = 310,
    kParamPartAttackCharacterBase = 320,
    kParamPartSpeedProfileBase = 330, // optional CC20: Auto/Slow/Normal/Fast for Cubase Expression Map
    // v3.8 Personal Taste / Judge Memory. 340+ deliberately avoids legacy part automation ranges.
    kParamPersonalTasteEnable = 340, kParamPersonalTasteStrength = 341, kParamPersonalTasteLearn = 342, kParamPersonalTasteClear = 343,
    kParamPersonalConfidence = 344, kParamPersonalEvidence = 345, kParamPersonalWeightBase = 346, // 346..350 Dyn/Atk/Trans/Stability/Safety
    kParamPersonalScoreBase = 351, // 351..354 A-D
    // v3.9 confidence-gated Preference Auto Comp.
    kParamPreferenceAutoComp = 355, kParamPreferenceMinConfidence = 356, kParamPreferenceMinMargin = 357, kParamPreferenceSafetyFloor = 358,
    kParamPreferenceAutoCompCancel = 359, kParamPreferenceAutoCompStatus = 360, kParamPreferenceAutoCompProgress = 361,
    kParamPreferenceAutoCompCommitted = 362, kParamPreferenceAutoCompReview = 363,
    // v4.1 strings-only 4x4 per-note voice lanes. 16 params per control family.
    kParamVoiceStackBase = 400,      // 400..415 CC21
    kParamVoiceDynamicsBase = 420,   // 420..435 CC22
    kParamVoiceVibratoBase = 440,    // 440..455 CC23
    kParamVoiceTransitionBase = 460, // 460..475 CC24
    kParamVoiceAttackBase = 480,     // 480..495 CC25
    kParamVoiceTightnessBase = 500,  // 500..515 CC26
    // v4.2 strings-only physical performance bus. 16 params per family.
    kParamVoiceStringBase = 520,       // 520..535 CC27
    kParamVoicePositionBase = 540,     // 540..555 CC28
    kParamVoiceBowDirectionBase = 560, // 560..575 CC29
    kParamVoiceBowChangeBase = 580,    // 580..595 CC30
    kParamVoiceBowPressureBase = 600,  // 600..615 CC31
    kParamVoiceContactPointBase = 620, // 620..635 CC33
    kParamVoicePortamentoBase = 640,   // 640..655 CC34
    kParamVoiceDeskBase = 660,         // 660..675 CC35
    // v4.4 ensemble timing: two compact per-lane families.
    kParamVoiceEnsembleAttackBase = 680, // 680..695 CC36 (-8..+8 ms)
    kParamVoicePhraseBreathBase = 700,   // 700..715 CC37 (0..20 ms)
    // v4.5 continuous gesture: compact opt-in + lane-local micro-pitch.
    kParamVoiceGestureAmountBase = 720,  // 720..735 CC38
    kParamVoiceMicroPitchBase = 740,      // 740..755 CC39 (+/-50 cents centered at .5)
    // v6.4 product front-end / stage-mixer controls. Kept outside all MIDI-facing ranges.
    kParamUiPage = 800,                   // controller UI page: Score / Perform / Retakes / Mix
    kParamStageMixerEnable = 810,
    kParamStageMasterGain = 811,
    kParamStageFeedGainBase = 812,        // 812..827 Spot/Tree/Wide/Room/Rear/Mid/Far/Gallery
    kParamStageOutputGain = 828,
};
inline Steinberg::Vst::ParamID voiceParam(Steinberg::Vst::ParamID base, int channel) {
    return base + static_cast<Steinberg::Vst::ParamID>(channel);
}
inline Steinberg::Vst::ParamID personalParam(Steinberg::Vst::ParamID base, int index) { return base + static_cast<Steinberg::Vst::ParamID>(index); }
inline Steinberg::Vst::ParamID judgeParam(Steinberg::Vst::ParamID base, int take) {
    return base + static_cast<Steinberg::Vst::ParamID>(take);
}
inline Steinberg::Vst::ParamID timelineParam(Steinberg::Vst::ParamID base, int slot) {
    return base + static_cast<Steinberg::Vst::ParamID>(slot);
}
inline Steinberg::Vst::ParamID partParam(Steinberg::Vst::ParamID base, int part) {
    return base + static_cast<Steinberg::Vst::ParamID>(part);
}
} // namespace
