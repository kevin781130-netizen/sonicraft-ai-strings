#pragma once
#include "public.sdk/source/vst/vstaudioeffect.h"
#include "preview_engine.h"
#include "tempo_timeline.h"
#include "shadow_render_client.h"
#include "host_cycle_scope_v31.h"
#include "retake_carousel_v32.h"
#include "take_comp_v33.h"
#include "persistent_take_comp_v34.h"
#include "performance_memory_v35.h"
#include "smart_comp_timeline_v36.h"
#include "preference_client_v38.h"
#include "preference_auto_comp_v39.h"
#include "string_expression_v41.h"
#include "string_physical_v42.h"
#include "string_ensemble_v44.h"
#include "string_gesture_v45.h"
#include "string_transition_v46.h"
#include <array>
#include <cstdint>
#include <limits>
namespace Sonicraft::AIStrings {
class Processor : public Steinberg::Vst::AudioEffect {
public:
    Processor();
    static Steinberg::FUnknown* createInstance(void*) { return (Steinberg::Vst::IAudioProcessor*)new Processor(); }
    Steinberg::tresult PLUGIN_API initialize(Steinberg::FUnknown* context) override;
    Steinberg::tresult PLUGIN_API setBusArrangements(Steinberg::Vst::SpeakerArrangement* inputs, Steinberg::int32 numIns, Steinberg::Vst::SpeakerArrangement* outputs, Steinberg::int32 numOuts) override;
    Steinberg::tresult PLUGIN_API setupProcessing(Steinberg::Vst::ProcessSetup& setup) override;
    Steinberg::tresult PLUGIN_API canProcessSampleSize(Steinberg::int32 symbolicSampleSize) override;
    Steinberg::tresult PLUGIN_API process(Steinberg::Vst::ProcessData& data) override;
    Steinberg::uint32 PLUGIN_API getProcessContextRequirements() override;
    Steinberg::tresult PLUGIN_API setState(Steinberg::IBStream* state) override;
    Steinberg::tresult PLUGIN_API getState(Steinberg::IBStream* state) override;
public:
    struct Controls { float dyn=.62f,vib=.50f,exp=.90f,vol=.86f,pan=.50f,sus=1.f,leg=1.f,room=.18f,bend=.50f,art=0.f,transition=.50f,tightness=.50f,attack=.38f,speedProfile=0.f,stack=0.f; };
    struct VoiceLaneOverride {
        float stack=0.f,dyn=.62f,vib=.50f,transition=.50f,attack=.38f,tightness=.50f,art=0.f,bend=.50f;
        std::uint8_t mask=0;
        StringPhysicalStateV42 physical{};
        std::uint8_t physicalMask=0;
        StringEnsembleStateV44 ensemble{};
        std::uint8_t ensembleMask=0;
        float gestureAmount=0.f;
    };
private:
    PreviewEngine engine;
    ShadowRenderClient shadow;
    PreferenceClientV38 preference;
    std::array<Controls,4> part{};
    float mode=0.f,activePart=0.f,humanize=.16f,aiMix=.85f,layoutMode=0.f,singleInstrument=0.f,aiAssist=.5f,lookAhead=.35f,autoDivisi=0.f;
    float performanceStyle=0.f,smartDynamics=0.f,smartArticulation=0.f,retakeTarget=0.f,retakeAmount=0.f,retakeNonce=0.f,stagePerspective=.333333f,polyphony=1.f;
    float midiAuthorityLock=1.f,phraseDirector=1.f,ensembleLooseness=.18f;
    // v6.4: optional microphone-mixer layer. Disabled by default so existing renders remain unchanged.
    float stageMixerEnable=0.f,stageMasterGain=1.f,stageOutputGain=1.f;
    std::array<float,16> stageFeedGain{{.25f,.35f,.25f,.45f,.62f,.45f,.28f,.28f,.20f,.20f,0.f,.12f,.12f,.06f,.06f,0.f}};
    float hostScopeMode=0.f,hostScopeStyle=0.f,hostScopeLooseness=.30f;
    float takeCarouselMode=0.f,takeCarouselSelect=0.f,takeCarouselFreeze=0.f;
    float takeCompMode=0.f,takeCompCommit=0.f,takeCompClear=0.f,takeCompPhraseLength=.25f;
    float takeCompUndo=0.f,takeCompRedo=0.f,takeCompFavorite=0.f,takeCompReject=0.f,takeCompCommitAll=0.f;
    RetakeCarouselTracker takeCarouselTracker;
    PersistentPhraseTakeComp phraseTakeComp;
    bool takeCompCommitLatch=false, takeCompClearLatch=false, takeCompUndoLatch=false, takeCompRedoLatch=false;
    bool takeCompFavoriteLatch=false, takeCompRejectLatch=false, takeCompCommitAllLatch=false;
    float memoryFollowPlayhead=1.f,memoryPrev=0.f,memoryNext=0.f,memoryNextUnresolved=0.f,memoryRecallTake=0.f;
    float memoryRecallApply=0.f,memoryCommitRecall=0.f,memoryFavoriteRecall=0.f,memoryRejectRecall=0.f,memoryClearPhrase=0.f;
    bool memoryPrevLatch=false,memoryNextLatch=false,memoryNextUnresolvedLatch=false,memoryRecallApplyLatch=false;
    bool memoryCommitRecallLatch=false,memoryFavoriteRecallLatch=false,memoryRejectRecallLatch=false,memoryClearPhraseLatch=false;
    std::int64_t memoryCursorKey=0;
    float smartRankMode=.5f,smartAudition=0.f,smartCommit=0.f,commitUniqueFavorites=0.f,autoCompUnresolved=0.f;
    bool smartAuditionLatch=false,smartCommitLatch=false,commitUniqueFavoritesLatch=false,autoCompUnresolvedLatch=false;
    float judgeTrigger=0.f,judgeAuditionWinner=0.f,judgeCommitWinner=0.f;
    bool judgeTriggerLatch=false,judgeAuditionWinnerLatch=false,judgeCommitWinnerLatch=false;
    float personalTasteEnable=1.f,personalTasteStrength=.75f,personalTasteLearn=1.f,personalTasteClear=0.f;
    bool personalTasteClearLatch=false;
    float preferenceAutoComp=0.f,preferenceMinConfidence=.30f,preferenceMinMargin=.10f,preferenceSafetyFloor=.35f,preferenceAutoCompCancel=0.f;
    bool preferenceAutoCompLatch=false,preferenceAutoCompCancelLatch=false,preferenceAutoCompRunning=false,preferenceAutoCompWaiting=false;
    uint32_t preferenceBatchId=0,preferenceJudgeGeneration=0; uint64_t preferencePendingToken=0; int64_t preferencePendingStart=0,preferencePendingKey=0;
    int preferenceJobCount=0,preferenceJobIndex=0,preferenceCandidateCount=0,preferenceReviewCount=0;
    std::array<std::int64_t,PersistentPhraseTakeComp::kCapacity> preferenceJobKeys{},preferenceCandidateKeys{};
    std::array<std::uint8_t,PersistentPhraseTakeComp::kCapacity> preferenceCandidateTakes{};
    std::array<VoiceLaneOverride,16> voiceLane{};
    std::array<std::array<int8_t,128>,16> divisiOwner{};
    std::array<int,4> divisiActive{{0,0,0,0}};
    int chooseDivisiPart(int note) const noexcept;
    double hostTempoBpm=68.0;
    TempoTimelineCapture tempoTimeline;
    int64_t lastProjectEnd=0;
    int64_t lastControlPush=std::numeric_limits<int64_t>::min();
};
}
