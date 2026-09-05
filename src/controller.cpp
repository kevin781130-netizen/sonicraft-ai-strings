#include "controller.h"
#include "ids.h"
#include "string_expression_v41.h"
#include "string_physical_v42.h"
#include "string_ensemble_v44.h"
#include "string_gesture_v45.h"
#include "articulations.h"
#include "base/source/fstreamer.h"
#include "public.sdk/source/vst/vstparameters.h"
#include "pluginterfaces/base/ustring.h"
#include <cstring>
using namespace Steinberg; using namespace Steinberg::Vst;
namespace Sonicraft::AIStrings {

Steinberg::IPlugView* PLUGIN_API Controller::createView(Steinberg::FIDString name) {
    if (name && std::strcmp(name, Steinberg::Vst::ViewType::kEditor) == 0) {
        auto* editor = new VSTGUI::VST3Editor(this, "MainView", "SONICRAFT_AI_Strings_Q4.uidesc");
        editor->setEditorSizeConstrains(VSTGUI::CPoint(900, 1000), VSTGUI::CPoint(1500, 1400));
        return editor;
    }
    return nullptr;
}

static void addPartParameters(ParameterContainer& p,int part,const TChar* dyn,const TChar* vib,const TChar* exp,const TChar* vol,const TChar* pan,const TChar* sus,const TChar* leg,const TChar* room,const TChar* bend,const TChar* art,const TChar* transition,const TChar* tightness,const TChar* attack,const TChar* speed){
    p.addParameter(dyn,nullptr,0,.62,ParameterInfo::kCanAutomate,partParam(kParamPartDynamicsBase,part));p.addParameter(vib,nullptr,0,.50,ParameterInfo::kCanAutomate,partParam(kParamPartVibratoBase,part));p.addParameter(exp,nullptr,0,.90,ParameterInfo::kCanAutomate,partParam(kParamPartExpressionBase,part));p.addParameter(vol,nullptr,0,.86,ParameterInfo::kCanAutomate,partParam(kParamPartVolumeBase,part));p.addParameter(pan,nullptr,0,.50,ParameterInfo::kCanAutomate,partParam(kParamPartPanBase,part));p.addParameter(sus,nullptr,1,1.,ParameterInfo::kCanAutomate,partParam(kParamPartSustainBase,part));p.addParameter(leg,nullptr,1,1.,ParameterInfo::kCanAutomate,partParam(kParamPartLegatoBase,part));p.addParameter(room,nullptr,0,.18,ParameterInfo::kCanAutomate,partParam(kParamPartRoomBase,part));p.addParameter(bend,nullptr,0,.50,ParameterInfo::kCanAutomate,partParam(kParamPartPitchBendBase,part));
    auto* a=new StringListParameter(art,partParam(kParamPartArticulationBase,part));for(const TChar* s:{STR16("Sustain"),STR16("Legato"),STR16("Portamento"),STR16("Expressive Long"),STR16("Marcato"),STR16("Staccato"),STR16("Spiccato"),STR16("Tremolo"),STR16("Pizzicato"),STR16("Trill"),STR16("Harmonic"),STR16("Flautando")})a->appendString(s);p.addParameter(a);
    p.addParameter(transition,nullptr,0,.50,ParameterInfo::kCanAutomate,partParam(kParamPartTransitionSpeedBase,part));p.addParameter(tightness,nullptr,0,.50,ParameterInfo::kCanAutomate,partParam(kParamPartShortTightnessBase,part));p.addParameter(attack,nullptr,0,.38,ParameterInfo::kCanAutomate,partParam(kParamPartAttackCharacterBase,part));
    auto* sp=new StringListParameter(speed,partParam(kParamPartSpeedProfileBase,part));sp->appendString(STR16("Auto Tempo"));sp->appendString(STR16("Slow"));sp->appendString(STR16("Normal"));sp->appendString(STR16("Fast"));p.addParameter(sp);
}
tresult PLUGIN_API Controller::initialize(FUnknown* context){auto r=EditControllerEx1::initialize(context);if(r!=kResultOk)return r;auto* mode=new StringListParameter(STR16("Mode"),kParamMode);mode->appendString(STR16("LIVE"));mode->appendString(STR16("AUTO"));mode->appendString(STR16("HQ"));parameters.addParameter(mode);auto* active=new StringListParameter(STR16("Active Part"),kParamActivePart);active->appendString(STR16("Vln I"));active->appendString(STR16("Vln II"));active->appendString(STR16("Viola"));active->appendString(STR16("Cello"));parameters.addParameter(active);parameters.addParameter(STR16("Humanize"),nullptr,0,.16,ParameterInfo::kCanAutomate,kParamHumanize);parameters.addParameter(STR16("AI Mix"),nullptr,0,.85,ParameterInfo::kCanAutomate,kParamAIMix);auto* layout=new StringListParameter(STR16("Layout"),kParamLayoutMode);layout->appendString(STR16("Single"));layout->appendString(STR16("Q4 Multi"));parameters.addParameter(layout);auto* ins=new StringListParameter(STR16("Single Section Instrument"),kParamSingleInstrument);for(const TChar* s:{STR16("Violin I"),STR16("Violin II"),STR16("Viola"),STR16("Cello")})ins->appendString(s);parameters.addParameter(ins);auto* assist=new StringListParameter(STR16("AI Performance Assist"),kParamAIAssist);assist->appendString(STR16("Manual"));assist->appendString(STR16("Assist"));assist->appendString(STR16("Auto"));parameters.addParameter(assist);parameters.addParameter(STR16("AI Look Ahead"),nullptr,0,.35,ParameterInfo::kCanAutomate,kParamLookAhead);parameters.addParameter(STR16("Auto Divisi"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamAutoDivisi);
    auto* style=new StringListParameter(STR16("Performance Style"),kParamPerformanceStyle);for(const TChar* x:{STR16("Neutral"),STR16("Adagio"),STR16("Allegro"),STR16("con Fuoco"),STR16("Pop"),STR16("Ballade")})style->appendString(x);parameters.addParameter(style);
    parameters.addParameter(STR16("Smart Dynamics"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamSmartDynamics);parameters.addParameter(STR16("Smart Articulation"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamSmartArticulation);
    auto* rt=new StringListParameter(STR16("Retake Target"),kParamRetakeTarget);for(const TChar* x:{STR16("Off"),STR16("Timbre"),STR16("Dynamics"),STR16("Vibrato"),STR16("Micro-Pitch"),STR16("Timing Feel"),STR16("Bow / Attack"),STR16("All")})rt->appendString(x);parameters.addParameter(rt);
    parameters.addParameter(STR16("Retake Amount"),nullptr,0,0.,ParameterInfo::kCanAutomate,kParamRetakeAmount);parameters.addParameter(STR16("Retake Seed"),nullptr,0,0.,ParameterInfo::kCanAutomate,kParamRetakeNonce);
    auto* st=new StringListParameter(STR16("Stage Perspective"),kParamStagePerspective);for(const TChar* x:{STR16("Dry"),STR16("Scoring"),STR16("Wide"),STR16("Room")})st->appendString(x);parameters.addParameter(st);parameters.addParameter(STR16("Independent Polyphony"),nullptr,1,1.,ParameterInfo::kCanAutomate,kParamPolyphony);
    auto* uiPage=new StringListParameter(STR16("UI Page"),kParamUiPage);for(const TChar* x:{STR16("Score"),STR16("Perform"),STR16("Retakes"),STR16("Mix")})uiPage->appendString(x);parameters.addParameter(uiPage);
    parameters.addParameter(STR16("Stage Mixer Enable"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamStageMixerEnable);
    parameters.addParameter(STR16("Stage Master"),nullptr,0,1.,ParameterInfo::kCanAutomate,kParamStageMasterGain);
    static const TChar* kFeedNames[16]={STR16("Spot L"),STR16("Spot C"),STR16("Spot R"),STR16("Tree L"),STR16("Tree C"),STR16("Tree R"),STR16("Wide L"),STR16("Wide R"),STR16("Room L"),STR16("Room R"),STR16("Rear"),STR16("Mid L"),STR16("Mid R"),STR16("Far L"),STR16("Far R"),STR16("Gallery")};
    static const double kFeedDefaults[16]={.25,.35,.25,.45,.62,.45,.28,.28,.20,.20,0.,.12,.12,.06,.06,0.};
    for(int i=0;i<16;++i)parameters.addParameter(kFeedNames[i],nullptr,0,kFeedDefaults[i],ParameterInfo::kCanAutomate,kParamStageFeedGainBase+i);
    parameters.addParameter(STR16("Stage Output"),nullptr,0,1.,ParameterInfo::kCanAutomate,kParamStageOutputGain);
    parameters.addParameter(STR16("MIDI Authority Lock"),nullptr,1,1.,ParameterInfo::kCanAutomate,kParamMidiAuthorityLock);
    parameters.addParameter(STR16("Phrase Director"),nullptr,1,1.,ParameterInfo::kCanAutomate,kParamPhraseDirector);
    parameters.addParameter(STR16("Ensemble Looseness"),nullptr,0,.18,ParameterInfo::kCanAutomate,kParamEnsembleLooseness);
    auto* hs=new StringListParameter(STR16("Host Scope"),kParamHostScopeMode);for(const TChar* x:{STR16("Off"),STR16("Locator Retake"),STR16("Locator Director"),STR16("Locator Both")})hs->appendString(x);parameters.addParameter(hs);
    auto* hss=new StringListParameter(STR16("Host Scope Style"),kParamHostScopeStyle);for(const TChar* x:{STR16("Neutral"),STR16("Adagio"),STR16("Allegro"),STR16("con Fuoco"),STR16("Pop"),STR16("Ballade")})hss->appendString(x);parameters.addParameter(hss);
    parameters.addParameter(STR16("Host Scope Looseness"),nullptr,0,.30,ParameterInfo::kCanAutomate,kParamHostScopeLooseness);
    auto* tbm=new StringListParameter(STR16("Take Bank Mode"),kParamTakeCarouselMode);for(const TChar* x:{STR16("Off"),STR16("Manual"),STR16("Auto Loop")})tbm->appendString(x);parameters.addParameter(tbm);
    auto* tbs=new StringListParameter(STR16("Take Select"),kParamTakeCarouselSelect);for(const TChar* x:{STR16("Take A"),STR16("Take B"),STR16("Take C"),STR16("Take D")})tbs->appendString(x);parameters.addParameter(tbs);
    parameters.addParameter(STR16("Freeze Current Take"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamTakeCarouselFreeze);
    auto* tcm=new StringListParameter(STR16("Take Comp Mode"),kParamTakeCompMode);for(const TChar* x:{STR16("Off"),STR16("Phrase Comp")})tcm->appendString(x);parameters.addParameter(tcm);
    parameters.addParameter(STR16("Commit Current Phrase"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamTakeCompCommit);
    parameters.addParameter(STR16("Clear Phrase Comp"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamTakeCompClear);
    parameters.addParameter(STR16("Comp Phrase Length"),nullptr,0,.25,ParameterInfo::kCanAutomate,kParamTakeCompPhraseLength);
    parameters.addParameter(STR16("Undo Comp Edit"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamTakeCompUndo);
    parameters.addParameter(STR16("Redo Comp Edit"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamTakeCompRedo);
    parameters.addParameter(STR16("Favorite Current Take"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamTakeCompFavorite);
    parameters.addParameter(STR16("Reject Current Take"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamTakeCompReject);
    parameters.addParameter(STR16("Commit Take Across Locator"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamTakeCompCommitAll);
    parameters.addParameter(STR16("Memory Follow Playhead"),nullptr,1,1.,ParameterInfo::kCanAutomate,kParamMemoryFollowPlayhead);
    parameters.addParameter(STR16("Memory Previous Phrase"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamMemoryPrev);
    parameters.addParameter(STR16("Memory Next Phrase"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamMemoryNext);
    parameters.addParameter(STR16("Memory Next Unresolved"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamMemoryNextUnresolved);
    auto* mrt=new StringListParameter(STR16("Memory Recall Take"),kParamMemoryRecallTake);for(const TChar* x:{STR16("Take A"),STR16("Take B"),STR16("Take C"),STR16("Take D")})mrt->appendString(x);parameters.addParameter(mrt);
    parameters.addParameter(STR16("Memory Audition Recall"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamMemoryRecallApply);
    parameters.addParameter(STR16("Memory Commit Recall"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamMemoryCommitRecall);
    parameters.addParameter(STR16("Memory Favorite Recall"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamMemoryFavoriteRecall);
    parameters.addParameter(STR16("Memory Reject Recall"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamMemoryRejectRecall);
    parameters.addParameter(STR16("Memory Committed Take"),nullptr,4,0.,ParameterInfo::kIsReadOnly,kParamMemoryCommittedTake);
    parameters.addParameter(STR16("Memory Recall Favorite"),nullptr,1,0.,ParameterInfo::kIsReadOnly,kParamMemoryRecallFavorite);
    parameters.addParameter(STR16("Memory Recall Rejected"),nullptr,1,0.,ParameterInfo::kIsReadOnly,kParamMemoryRecallRejected);
    parameters.addParameter(STR16("Memory Locator Coverage"),nullptr,0,0.,ParameterInfo::kIsReadOnly,kParamMemoryCoverage);
    parameters.addParameter(STR16("Memory Cursor Position"),nullptr,0,0.,ParameterInfo::kIsReadOnly,kParamMemoryCursorPosition);
    parameters.addParameter(STR16("Memory Clear Phrase"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamMemoryClearPhrase);
    parameters.addParameter(STR16("Timeline 1 Committed"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineCommittedBase,0));
    parameters.addParameter(STR16("Timeline 2 Committed"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineCommittedBase,1));
    parameters.addParameter(STR16("Timeline 3 Committed"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineCommittedBase,2));
    parameters.addParameter(STR16("Timeline 4 Committed"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineCommittedBase,3));
    parameters.addParameter(STR16("Timeline 5 Committed"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineCommittedBase,4));
    parameters.addParameter(STR16("Timeline 6 Committed"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineCommittedBase,5));
    parameters.addParameter(STR16("Timeline 7 Committed"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineCommittedBase,6));
    parameters.addParameter(STR16("Timeline 8 Committed"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineCommittedBase,7));
    parameters.addParameter(STR16("Timeline 1 Smart Pick"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineSmartPickBase,0));
    parameters.addParameter(STR16("Timeline 2 Smart Pick"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineSmartPickBase,1));
    parameters.addParameter(STR16("Timeline 3 Smart Pick"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineSmartPickBase,2));
    parameters.addParameter(STR16("Timeline 4 Smart Pick"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineSmartPickBase,3));
    parameters.addParameter(STR16("Timeline 5 Smart Pick"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineSmartPickBase,4));
    parameters.addParameter(STR16("Timeline 6 Smart Pick"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineSmartPickBase,5));
    parameters.addParameter(STR16("Timeline 7 Smart Pick"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineSmartPickBase,6));
    parameters.addParameter(STR16("Timeline 8 Smart Pick"),nullptr,4,0.,ParameterInfo::kIsReadOnly,timelineParam(kParamTimelineSmartPickBase,7));
    auto* srm=new StringListParameter(STR16("Smart Rank Mode"),kParamSmartRankMode);for(const TChar* x:{STR16("Conservative"),STR16("Balanced"),STR16("Adventurous")})srm->appendString(x);parameters.addParameter(srm);
    parameters.addParameter(STR16("Smart Audition Suggested"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamSmartAudition);
    parameters.addParameter(STR16("Smart Commit Suggested"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamSmartCommit);
    parameters.addParameter(STR16("Smart Candidate Score"),nullptr,0,0.,ParameterInfo::kIsReadOnly,kParamSmartScore);
    parameters.addParameter(STR16("Timeline Cursor Slot"),nullptr,7,0.,ParameterInfo::kIsReadOnly,kParamTimelineCursorSlot);
    parameters.addParameter(STR16("Commit Unique Favorites"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamCommitUniqueFavorites);
    parameters.addParameter(STR16("Heuristic Auto Comp Unresolved"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamAutoCompUnresolved);
    parameters.addParameter(STR16("Smart Variation Priority"),nullptr,0,0.,ParameterInfo::kIsReadOnly,kParamSmartVariation);
    parameters.addParameter(STR16("Timeline Unresolved"),nullptr,0,0.,ParameterInfo::kIsReadOnly,kParamTimelineUnresolved);
    parameters.addParameter(STR16("Run Audio Take Judge"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamJudgeTrigger);
    parameters.addParameter(STR16("Audio Judge Winner"),nullptr,4,0.,ParameterInfo::kIsReadOnly,kParamJudgeWinner);
    parameters.addParameter(STR16("Judge A Overall"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeOverallBase,0));
    parameters.addParameter(STR16("Judge B Overall"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeOverallBase,1));
    parameters.addParameter(STR16("Judge C Overall"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeOverallBase,2));
    parameters.addParameter(STR16("Judge D Overall"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeOverallBase,3));
    parameters.addParameter(STR16("Judge A Dynamics"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeDynamicsBase,0));
    parameters.addParameter(STR16("Judge B Dynamics"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeDynamicsBase,1));
    parameters.addParameter(STR16("Judge C Dynamics"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeDynamicsBase,2));
    parameters.addParameter(STR16("Judge D Dynamics"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeDynamicsBase,3));
    parameters.addParameter(STR16("Judge A Attack"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeAttackBase,0));
    parameters.addParameter(STR16("Judge B Attack"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeAttackBase,1));
    parameters.addParameter(STR16("Judge C Attack"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeAttackBase,2));
    parameters.addParameter(STR16("Judge D Attack"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeAttackBase,3));
    parameters.addParameter(STR16("Judge A Transition"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeTransitionBase,0));
    parameters.addParameter(STR16("Judge B Transition"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeTransitionBase,1));
    parameters.addParameter(STR16("Judge C Transition"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeTransitionBase,2));
    parameters.addParameter(STR16("Judge D Transition"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeTransitionBase,3));
    parameters.addParameter(STR16("Judge A Stability"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeStabilityBase,0));
    parameters.addParameter(STR16("Judge B Stability"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeStabilityBase,1));
    parameters.addParameter(STR16("Judge C Stability"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeStabilityBase,2));
    parameters.addParameter(STR16("Judge D Stability"),nullptr,0,0.,ParameterInfo::kIsReadOnly,judgeParam(kParamJudgeStabilityBase,3));
    parameters.addParameter(STR16("Judge Winner Safety"),nullptr,0,0.,ParameterInfo::kIsReadOnly,kParamJudgeWinnerSafety);
    parameters.addParameter(STR16("Audition Judge Winner"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamJudgeAuditionWinner);
    parameters.addParameter(STR16("Commit Judge Winner"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamJudgeCommitWinner);
    parameters.addParameter(STR16("Personal Taste Enable"),nullptr,1,1.,ParameterInfo::kCanAutomate,kParamPersonalTasteEnable);
    parameters.addParameter(STR16("Personal Taste Strength"),nullptr,0,.75,ParameterInfo::kCanAutomate,kParamPersonalTasteStrength);
    parameters.addParameter(STR16("Learn My Choices"),nullptr,1,1.,ParameterInfo::kCanAutomate,kParamPersonalTasteLearn);
    parameters.addParameter(STR16("Clear Personal Taste"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamPersonalTasteClear);
    parameters.addParameter(STR16("Personal Confidence"),nullptr,0,0.,ParameterInfo::kIsReadOnly,kParamPersonalConfidence);
    parameters.addParameter(STR16("Personal Evidence"),nullptr,0,0.,ParameterInfo::kIsReadOnly,kParamPersonalEvidence);
    for(int i=0;i<5;++i)parameters.addParameter(STR16("Personal Weight"),nullptr,0,.5,ParameterInfo::kIsReadOnly,personalParam(kParamPersonalWeightBase,i));
    for(int i=0;i<4;++i)parameters.addParameter(STR16("Personal Take Score"),nullptr,0,0.,ParameterInfo::kIsReadOnly,personalParam(kParamPersonalScoreBase,i));
    parameters.addParameter(STR16("Preference Auto Comp"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamPreferenceAutoComp);
    parameters.addParameter(STR16("Auto Comp Min Confidence"),nullptr,0,.30,ParameterInfo::kCanAutomate,kParamPreferenceMinConfidence);
    parameters.addParameter(STR16("Auto Comp Min Margin"),nullptr,0,.10,ParameterInfo::kCanAutomate,kParamPreferenceMinMargin);
    parameters.addParameter(STR16("Auto Comp Safety Floor"),nullptr,0,.35,ParameterInfo::kCanAutomate,kParamPreferenceSafetyFloor);
    parameters.addParameter(STR16("Cancel Preference Auto Comp"),nullptr,1,0.,ParameterInfo::kCanAutomate,kParamPreferenceAutoCompCancel);
    auto* pas=new StringListParameter(STR16("Preference Auto Comp Status"),kParamPreferenceAutoCompStatus);for(const TChar*x:{STR16("Idle"),STR16("Queue"),STR16("Judging"),STR16("Done")})pas->appendString(x);parameters.addParameter(pas);
    parameters.addParameter(STR16("Preference Auto Comp Progress"),nullptr,0,0.,ParameterInfo::kIsReadOnly,kParamPreferenceAutoCompProgress);
    parameters.addParameter(STR16("Preference Auto Comp Committed"),nullptr,0,0.,ParameterInfo::kIsReadOnly,kParamPreferenceAutoCompCommitted);
    parameters.addParameter(STR16("Preference Auto Comp Needs Review"),nullptr,0,0.,ParameterInfo::kIsReadOnly,kParamPreferenceAutoCompReview);
    addPartParameters(parameters,0,STR16("Vln I Dynamics CC1"),STR16("Vln I Vibrato Depth CC3"),STR16("Vln I Expression CC11"),STR16("Vln I Volume CC7"),STR16("Vln I Pan CC10"),STR16("Vln I Sustain CC64"),STR16("Vln I Legato CC68"),STR16("Vln I Room CC91"),STR16("Vln I Pitch Bend"),STR16("Vln I Articulation"),STR16("Vln I Transition Speed"),STR16("Vln I Short Tightness"),STR16("Vln I Attack Character"),STR16("Vln I AI Speed Profile CC20"));
    addPartParameters(parameters,1,STR16("Vln II Dynamics CC1"),STR16("Vln II Vibrato Depth CC3"),STR16("Vln II Expression CC11"),STR16("Vln II Volume CC7"),STR16("Vln II Pan CC10"),STR16("Vln II Sustain CC64"),STR16("Vln II Legato CC68"),STR16("Vln II Room CC91"),STR16("Vln II Pitch Bend"),STR16("Vln II Articulation"),STR16("Vln II Transition Speed"),STR16("Vln II Short Tightness"),STR16("Vln II Attack Character"),STR16("Vln II AI Speed Profile CC20"));
    addPartParameters(parameters,2,STR16("Viola Dynamics CC1"),STR16("Viola Vibrato Depth CC3"),STR16("Viola Expression CC11"),STR16("Viola Volume CC7"),STR16("Viola Pan CC10"),STR16("Viola Sustain CC64"),STR16("Viola Legato CC68"),STR16("Viola Room CC91"),STR16("Viola Pitch Bend"),STR16("Viola Articulation"),STR16("Viola Transition Speed"),STR16("Viola Short Tightness"),STR16("Viola Attack Character"),STR16("Viola AI Speed Profile CC20"));
    addPartParameters(parameters,3,STR16("Cello Dynamics CC1"),STR16("Cello Vibrato Depth CC3"),STR16("Cello Expression CC11"),STR16("Cello Volume CC7"),STR16("Cello Pan CC10"),STR16("Cello Sustain CC64"),STR16("Cello Legato CC68"),STR16("Cello Room CC91"),STR16("Cello Pitch Bend"),STR16("Cello Articulation"),STR16("Cello Transition Speed"),STR16("Cello Short Tightness"),STR16("Cello Attack Character"),STR16("Cello AI Speed Profile CC20"));
    parameters.addParameter(STR16("String Voice 01 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,0));
    parameters.addParameter(STR16("String Voice 01 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,0));
    parameters.addParameter(STR16("String Voice 01 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,0));
    parameters.addParameter(STR16("String Voice 01 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,0));
    parameters.addParameter(STR16("String Voice 01 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,0));
    parameters.addParameter(STR16("String Voice 01 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,0));
    parameters.addParameter(STR16("String Voice 02 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,1));
    parameters.addParameter(STR16("String Voice 02 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,1));
    parameters.addParameter(STR16("String Voice 02 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,1));
    parameters.addParameter(STR16("String Voice 02 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,1));
    parameters.addParameter(STR16("String Voice 02 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,1));
    parameters.addParameter(STR16("String Voice 02 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,1));
    parameters.addParameter(STR16("String Voice 03 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,2));
    parameters.addParameter(STR16("String Voice 03 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,2));
    parameters.addParameter(STR16("String Voice 03 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,2));
    parameters.addParameter(STR16("String Voice 03 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,2));
    parameters.addParameter(STR16("String Voice 03 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,2));
    parameters.addParameter(STR16("String Voice 03 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,2));
    parameters.addParameter(STR16("String Voice 04 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,3));
    parameters.addParameter(STR16("String Voice 04 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,3));
    parameters.addParameter(STR16("String Voice 04 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,3));
    parameters.addParameter(STR16("String Voice 04 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,3));
    parameters.addParameter(STR16("String Voice 04 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,3));
    parameters.addParameter(STR16("String Voice 04 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,3));
    parameters.addParameter(STR16("String Voice 05 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,4));
    parameters.addParameter(STR16("String Voice 05 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,4));
    parameters.addParameter(STR16("String Voice 05 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,4));
    parameters.addParameter(STR16("String Voice 05 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,4));
    parameters.addParameter(STR16("String Voice 05 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,4));
    parameters.addParameter(STR16("String Voice 05 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,4));
    parameters.addParameter(STR16("String Voice 06 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,5));
    parameters.addParameter(STR16("String Voice 06 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,5));
    parameters.addParameter(STR16("String Voice 06 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,5));
    parameters.addParameter(STR16("String Voice 06 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,5));
    parameters.addParameter(STR16("String Voice 06 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,5));
    parameters.addParameter(STR16("String Voice 06 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,5));
    parameters.addParameter(STR16("String Voice 07 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,6));
    parameters.addParameter(STR16("String Voice 07 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,6));
    parameters.addParameter(STR16("String Voice 07 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,6));
    parameters.addParameter(STR16("String Voice 07 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,6));
    parameters.addParameter(STR16("String Voice 07 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,6));
    parameters.addParameter(STR16("String Voice 07 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,6));
    parameters.addParameter(STR16("String Voice 08 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,7));
    parameters.addParameter(STR16("String Voice 08 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,7));
    parameters.addParameter(STR16("String Voice 08 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,7));
    parameters.addParameter(STR16("String Voice 08 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,7));
    parameters.addParameter(STR16("String Voice 08 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,7));
    parameters.addParameter(STR16("String Voice 08 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,7));
    parameters.addParameter(STR16("String Voice 09 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,8));
    parameters.addParameter(STR16("String Voice 09 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,8));
    parameters.addParameter(STR16("String Voice 09 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,8));
    parameters.addParameter(STR16("String Voice 09 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,8));
    parameters.addParameter(STR16("String Voice 09 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,8));
    parameters.addParameter(STR16("String Voice 09 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,8));
    parameters.addParameter(STR16("String Voice 10 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,9));
    parameters.addParameter(STR16("String Voice 10 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,9));
    parameters.addParameter(STR16("String Voice 10 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,9));
    parameters.addParameter(STR16("String Voice 10 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,9));
    parameters.addParameter(STR16("String Voice 10 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,9));
    parameters.addParameter(STR16("String Voice 10 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,9));
    parameters.addParameter(STR16("String Voice 11 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,10));
    parameters.addParameter(STR16("String Voice 11 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,10));
    parameters.addParameter(STR16("String Voice 11 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,10));
    parameters.addParameter(STR16("String Voice 11 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,10));
    parameters.addParameter(STR16("String Voice 11 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,10));
    parameters.addParameter(STR16("String Voice 11 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,10));
    parameters.addParameter(STR16("String Voice 12 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,11));
    parameters.addParameter(STR16("String Voice 12 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,11));
    parameters.addParameter(STR16("String Voice 12 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,11));
    parameters.addParameter(STR16("String Voice 12 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,11));
    parameters.addParameter(STR16("String Voice 12 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,11));
    parameters.addParameter(STR16("String Voice 12 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,11));
    parameters.addParameter(STR16("String Voice 13 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,12));
    parameters.addParameter(STR16("String Voice 13 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,12));
    parameters.addParameter(STR16("String Voice 13 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,12));
    parameters.addParameter(STR16("String Voice 13 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,12));
    parameters.addParameter(STR16("String Voice 13 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,12));
    parameters.addParameter(STR16("String Voice 13 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,12));
    parameters.addParameter(STR16("String Voice 14 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,13));
    parameters.addParameter(STR16("String Voice 14 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,13));
    parameters.addParameter(STR16("String Voice 14 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,13));
    parameters.addParameter(STR16("String Voice 14 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,13));
    parameters.addParameter(STR16("String Voice 14 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,13));
    parameters.addParameter(STR16("String Voice 14 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,13));
    parameters.addParameter(STR16("String Voice 15 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,14));
    parameters.addParameter(STR16("String Voice 15 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,14));
    parameters.addParameter(STR16("String Voice 15 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,14));
    parameters.addParameter(STR16("String Voice 15 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,14));
    parameters.addParameter(STR16("String Voice 15 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,14));
    parameters.addParameter(STR16("String Voice 15 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,14));
    parameters.addParameter(STR16("String Voice 16 Stack CC21"),nullptr,15,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStackBase,15));
    parameters.addParameter(STR16("String Voice 16 Dynamics CC22"),nullptr,0,.62,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDynamicsBase,15));
    parameters.addParameter(STR16("String Voice 16 Vibrato CC23"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceVibratoBase,15));
    parameters.addParameter(STR16("String Voice 16 Transition CC24"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTransitionBase,15));
    parameters.addParameter(STR16("String Voice 16 Attack CC25"),nullptr,0,.38,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceAttackBase,15));
    parameters.addParameter(STR16("String Voice 16 Tightness CC26"),nullptr,0,.50,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceTightnessBase,15));

    parameters.addParameter(STR16("String Voice 01 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,0));
    parameters.addParameter(STR16("String Voice 01 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,0));
    parameters.addParameter(STR16("String Voice 01 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,0));
    parameters.addParameter(STR16("String Voice 01 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,0));
    parameters.addParameter(STR16("String Voice 01 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,0));
    parameters.addParameter(STR16("String Voice 01 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,0));
    parameters.addParameter(STR16("String Voice 01 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,0));
    parameters.addParameter(STR16("String Voice 01 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,0));
    parameters.addParameter(STR16("String Voice 02 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,1));
    parameters.addParameter(STR16("String Voice 02 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,1));
    parameters.addParameter(STR16("String Voice 02 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,1));
    parameters.addParameter(STR16("String Voice 02 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,1));
    parameters.addParameter(STR16("String Voice 02 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,1));
    parameters.addParameter(STR16("String Voice 02 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,1));
    parameters.addParameter(STR16("String Voice 02 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,1));
    parameters.addParameter(STR16("String Voice 02 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,1));
    parameters.addParameter(STR16("String Voice 03 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,2));
    parameters.addParameter(STR16("String Voice 03 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,2));
    parameters.addParameter(STR16("String Voice 03 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,2));
    parameters.addParameter(STR16("String Voice 03 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,2));
    parameters.addParameter(STR16("String Voice 03 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,2));
    parameters.addParameter(STR16("String Voice 03 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,2));
    parameters.addParameter(STR16("String Voice 03 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,2));
    parameters.addParameter(STR16("String Voice 03 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,2));
    parameters.addParameter(STR16("String Voice 04 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,3));
    parameters.addParameter(STR16("String Voice 04 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,3));
    parameters.addParameter(STR16("String Voice 04 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,3));
    parameters.addParameter(STR16("String Voice 04 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,3));
    parameters.addParameter(STR16("String Voice 04 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,3));
    parameters.addParameter(STR16("String Voice 04 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,3));
    parameters.addParameter(STR16("String Voice 04 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,3));
    parameters.addParameter(STR16("String Voice 04 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,3));
    parameters.addParameter(STR16("String Voice 05 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,4));
    parameters.addParameter(STR16("String Voice 05 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,4));
    parameters.addParameter(STR16("String Voice 05 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,4));
    parameters.addParameter(STR16("String Voice 05 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,4));
    parameters.addParameter(STR16("String Voice 05 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,4));
    parameters.addParameter(STR16("String Voice 05 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,4));
    parameters.addParameter(STR16("String Voice 05 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,4));
    parameters.addParameter(STR16("String Voice 05 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,4));
    parameters.addParameter(STR16("String Voice 06 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,5));
    parameters.addParameter(STR16("String Voice 06 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,5));
    parameters.addParameter(STR16("String Voice 06 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,5));
    parameters.addParameter(STR16("String Voice 06 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,5));
    parameters.addParameter(STR16("String Voice 06 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,5));
    parameters.addParameter(STR16("String Voice 06 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,5));
    parameters.addParameter(STR16("String Voice 06 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,5));
    parameters.addParameter(STR16("String Voice 06 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,5));
    parameters.addParameter(STR16("String Voice 07 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,6));
    parameters.addParameter(STR16("String Voice 07 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,6));
    parameters.addParameter(STR16("String Voice 07 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,6));
    parameters.addParameter(STR16("String Voice 07 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,6));
    parameters.addParameter(STR16("String Voice 07 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,6));
    parameters.addParameter(STR16("String Voice 07 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,6));
    parameters.addParameter(STR16("String Voice 07 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,6));
    parameters.addParameter(STR16("String Voice 07 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,6));
    parameters.addParameter(STR16("String Voice 08 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,7));
    parameters.addParameter(STR16("String Voice 08 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,7));
    parameters.addParameter(STR16("String Voice 08 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,7));
    parameters.addParameter(STR16("String Voice 08 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,7));
    parameters.addParameter(STR16("String Voice 08 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,7));
    parameters.addParameter(STR16("String Voice 08 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,7));
    parameters.addParameter(STR16("String Voice 08 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,7));
    parameters.addParameter(STR16("String Voice 08 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,7));
    parameters.addParameter(STR16("String Voice 09 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,8));
    parameters.addParameter(STR16("String Voice 09 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,8));
    parameters.addParameter(STR16("String Voice 09 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,8));
    parameters.addParameter(STR16("String Voice 09 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,8));
    parameters.addParameter(STR16("String Voice 09 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,8));
    parameters.addParameter(STR16("String Voice 09 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,8));
    parameters.addParameter(STR16("String Voice 09 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,8));
    parameters.addParameter(STR16("String Voice 09 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,8));
    parameters.addParameter(STR16("String Voice 10 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,9));
    parameters.addParameter(STR16("String Voice 10 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,9));
    parameters.addParameter(STR16("String Voice 10 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,9));
    parameters.addParameter(STR16("String Voice 10 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,9));
    parameters.addParameter(STR16("String Voice 10 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,9));
    parameters.addParameter(STR16("String Voice 10 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,9));
    parameters.addParameter(STR16("String Voice 10 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,9));
    parameters.addParameter(STR16("String Voice 10 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,9));
    parameters.addParameter(STR16("String Voice 11 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,10));
    parameters.addParameter(STR16("String Voice 11 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,10));
    parameters.addParameter(STR16("String Voice 11 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,10));
    parameters.addParameter(STR16("String Voice 11 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,10));
    parameters.addParameter(STR16("String Voice 11 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,10));
    parameters.addParameter(STR16("String Voice 11 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,10));
    parameters.addParameter(STR16("String Voice 11 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,10));
    parameters.addParameter(STR16("String Voice 11 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,10));
    parameters.addParameter(STR16("String Voice 12 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,11));
    parameters.addParameter(STR16("String Voice 12 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,11));
    parameters.addParameter(STR16("String Voice 12 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,11));
    parameters.addParameter(STR16("String Voice 12 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,11));
    parameters.addParameter(STR16("String Voice 12 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,11));
    parameters.addParameter(STR16("String Voice 12 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,11));
    parameters.addParameter(STR16("String Voice 12 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,11));
    parameters.addParameter(STR16("String Voice 12 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,11));
    parameters.addParameter(STR16("String Voice 13 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,12));
    parameters.addParameter(STR16("String Voice 13 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,12));
    parameters.addParameter(STR16("String Voice 13 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,12));
    parameters.addParameter(STR16("String Voice 13 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,12));
    parameters.addParameter(STR16("String Voice 13 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,12));
    parameters.addParameter(STR16("String Voice 13 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,12));
    parameters.addParameter(STR16("String Voice 13 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,12));
    parameters.addParameter(STR16("String Voice 13 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,12));
    parameters.addParameter(STR16("String Voice 14 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,13));
    parameters.addParameter(STR16("String Voice 14 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,13));
    parameters.addParameter(STR16("String Voice 14 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,13));
    parameters.addParameter(STR16("String Voice 14 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,13));
    parameters.addParameter(STR16("String Voice 14 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,13));
    parameters.addParameter(STR16("String Voice 14 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,13));
    parameters.addParameter(STR16("String Voice 14 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,13));
    parameters.addParameter(STR16("String Voice 14 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,13));
    parameters.addParameter(STR16("String Voice 15 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,14));
    parameters.addParameter(STR16("String Voice 15 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,14));
    parameters.addParameter(STR16("String Voice 15 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,14));
    parameters.addParameter(STR16("String Voice 15 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,14));
    parameters.addParameter(STR16("String Voice 15 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,14));
    parameters.addParameter(STR16("String Voice 15 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,14));
    parameters.addParameter(STR16("String Voice 15 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,14));
    parameters.addParameter(STR16("String Voice 15 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,14));
    parameters.addParameter(STR16("String Voice 16 String CC27"),nullptr,3,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceStringBase,15));
    parameters.addParameter(STR16("String Voice 16 Position CC28"),nullptr,8,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePositionBase,15));
    parameters.addParameter(STR16("String Voice 16 Bow Direction CC29"),nullptr,1,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowDirectionBase,15));
    parameters.addParameter(STR16("String Voice 16 Bow Change CC30"),nullptr,1,1.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowChangeBase,15));
    parameters.addParameter(STR16("String Voice 16 Bow Pressure CC31"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceBowPressureBase,15));
    parameters.addParameter(STR16("String Voice 16 Contact Point CC33"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceContactPointBase,15));
    parameters.addParameter(STR16("String Voice 16 Portamento Route CC34"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePortamentoBase,15));
    parameters.addParameter(STR16("String Voice 16 Divisi Desk CC35"),nullptr,3,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceDeskBase,15));

    parameters.addParameter(STR16("String Voice 01 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,0));
    parameters.addParameter(STR16("String Voice 01 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,0));
    parameters.addParameter(STR16("String Voice 02 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,1));
    parameters.addParameter(STR16("String Voice 02 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,1));
    parameters.addParameter(STR16("String Voice 03 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,2));
    parameters.addParameter(STR16("String Voice 03 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,2));
    parameters.addParameter(STR16("String Voice 04 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,3));
    parameters.addParameter(STR16("String Voice 04 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,3));
    parameters.addParameter(STR16("String Voice 05 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,4));
    parameters.addParameter(STR16("String Voice 05 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,4));
    parameters.addParameter(STR16("String Voice 06 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,5));
    parameters.addParameter(STR16("String Voice 06 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,5));
    parameters.addParameter(STR16("String Voice 07 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,6));
    parameters.addParameter(STR16("String Voice 07 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,6));
    parameters.addParameter(STR16("String Voice 08 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,7));
    parameters.addParameter(STR16("String Voice 08 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,7));
    parameters.addParameter(STR16("String Voice 09 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,8));
    parameters.addParameter(STR16("String Voice 09 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,8));
    parameters.addParameter(STR16("String Voice 10 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,9));
    parameters.addParameter(STR16("String Voice 10 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,9));
    parameters.addParameter(STR16("String Voice 11 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,10));
    parameters.addParameter(STR16("String Voice 11 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,10));
    parameters.addParameter(STR16("String Voice 12 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,11));
    parameters.addParameter(STR16("String Voice 12 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,11));
    parameters.addParameter(STR16("String Voice 13 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,12));
    parameters.addParameter(STR16("String Voice 13 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,12));
    parameters.addParameter(STR16("String Voice 14 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,13));
    parameters.addParameter(STR16("String Voice 14 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,13));
    parameters.addParameter(STR16("String Voice 15 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,14));
    parameters.addParameter(STR16("String Voice 15 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,14));
    parameters.addParameter(STR16("String Voice 16 Ensemble Attack CC36"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceEnsembleAttackBase,15));
    parameters.addParameter(STR16("String Voice 16 Phrase Breath CC37"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoicePhraseBreathBase,15));

    parameters.addParameter(STR16("String Voice 01 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,0));
    parameters.addParameter(STR16("String Voice 01 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,0));
    parameters.addParameter(STR16("String Voice 02 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,1));
    parameters.addParameter(STR16("String Voice 02 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,1));
    parameters.addParameter(STR16("String Voice 03 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,2));
    parameters.addParameter(STR16("String Voice 03 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,2));
    parameters.addParameter(STR16("String Voice 04 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,3));
    parameters.addParameter(STR16("String Voice 04 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,3));
    parameters.addParameter(STR16("String Voice 05 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,4));
    parameters.addParameter(STR16("String Voice 05 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,4));
    parameters.addParameter(STR16("String Voice 06 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,5));
    parameters.addParameter(STR16("String Voice 06 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,5));
    parameters.addParameter(STR16("String Voice 07 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,6));
    parameters.addParameter(STR16("String Voice 07 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,6));
    parameters.addParameter(STR16("String Voice 08 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,7));
    parameters.addParameter(STR16("String Voice 08 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,7));
    parameters.addParameter(STR16("String Voice 09 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,8));
    parameters.addParameter(STR16("String Voice 09 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,8));
    parameters.addParameter(STR16("String Voice 10 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,9));
    parameters.addParameter(STR16("String Voice 10 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,9));
    parameters.addParameter(STR16("String Voice 11 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,10));
    parameters.addParameter(STR16("String Voice 11 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,10));
    parameters.addParameter(STR16("String Voice 12 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,11));
    parameters.addParameter(STR16("String Voice 12 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,11));
    parameters.addParameter(STR16("String Voice 13 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,12));
    parameters.addParameter(STR16("String Voice 13 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,12));
    parameters.addParameter(STR16("String Voice 14 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,13));
    parameters.addParameter(STR16("String Voice 14 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,13));
    parameters.addParameter(STR16("String Voice 15 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,14));
    parameters.addParameter(STR16("String Voice 15 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,14));
    parameters.addParameter(STR16("String Voice 16 Gesture Amount CC38"),nullptr,0,0.,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceGestureAmountBase,15));
    parameters.addParameter(STR16("String Voice 16 Micro Pitch CC39"),nullptr,0,.5,ParameterInfo::kCanAutomate,voiceParam(kParamVoiceMicroPitchBase,15));
    return kResultOk;}
tresult PLUGIN_API Controller::getMidiControllerAssignment(int32 busIndex,int16 channel,CtrlNumber cc,ParamID& id){
    if(busIndex!=0||channel<0||channel>=16)return kResultFalse;
    // v3.0 global command lane: duplicate these CCs on any Q4 channel. This keeps one
    // multi-timbral instance and four independent instances equally portable in a DAW.
    switch(cc){
        case kCC_AIAssist:id=kParamAIAssist;return kResultTrue;
        case kCC_PerformanceStyle:id=kParamPerformanceStyle;return kResultTrue;
        case kCC_SmartDynamics:id=kParamSmartDynamics;return kResultTrue;
        case kCC_SmartArticulation:id=kParamSmartArticulation;return kResultTrue;
        case kCC_RetakeTarget:id=kParamRetakeTarget;return kResultTrue;
        case kCC_RetakeAmount:id=kParamRetakeAmount;return kResultTrue;
        case kCC_RetakeSeed:id=kParamRetakeNonce;return kResultTrue;
        case kCC_MidiAuthorityLock:id=kParamMidiAuthorityLock;return kResultTrue;
        case kCC_PhraseDirector:id=kParamPhraseDirector;return kResultTrue;
        case kCC_EnsembleLooseness:id=kParamEnsembleLooseness;return kResultTrue;
        case kCC_AutoDivisi:id=kParamAutoDivisi;return kResultTrue;
        case kCC_StagePerspective:id=kParamStagePerspective;return kResultTrue;
        case kCC_IndependentPolyphony:id=kParamPolyphony;return kResultTrue;
        case kCC_AIMix:id=kParamAIMix;return kResultTrue;
        case kCC_AILookAhead:id=kParamLookAhead;return kResultTrue;
        case kCC_LayoutMode:id=kParamLayoutMode;return kResultTrue;
        case kCC_SingleInstrument:id=kParamSingleInstrument;return kResultTrue;
        case kCC_Humanize:id=kParamHumanize;return kResultTrue;
        default:break;
    }
    // v4.1-v4.5 dedicated per-note String Voice Bus controls.
    switch(cc){
        case 38:id=voiceParam(kParamVoiceGestureAmountBase,channel);return kResultTrue;
        case 39:id=voiceParam(kParamVoiceMicroPitchBase,channel);return kResultTrue;
        case 36:id=voiceParam(kParamVoiceEnsembleAttackBase,channel);return kResultTrue;
        case 37:id=voiceParam(kParamVoicePhraseBreathBase,channel);return kResultTrue;
        case 27:id=voiceParam(kParamVoiceStringBase,channel);return kResultTrue;
        case 28:id=voiceParam(kParamVoicePositionBase,channel);return kResultTrue;
        case 29:id=voiceParam(kParamVoiceBowDirectionBase,channel);return kResultTrue;
        case 30:id=voiceParam(kParamVoiceBowChangeBase,channel);return kResultTrue;
        case 31:id=voiceParam(kParamVoiceBowPressureBase,channel);return kResultTrue;
        case 33:id=voiceParam(kParamVoiceContactPointBase,channel);return kResultTrue;
        case 34:id=voiceParam(kParamVoicePortamentoBase,channel);return kResultTrue;
        case 35:id=voiceParam(kParamVoiceDeskBase,channel);return kResultTrue;
        case 21:id=voiceParam(kParamVoiceStackBase,channel);return kResultTrue;
        case 22:id=voiceParam(kParamVoiceDynamicsBase,channel);return kResultTrue;
        case 23:id=voiceParam(kParamVoiceVibratoBase,channel);return kResultTrue;
        case 24:id=voiceParam(kParamVoiceTransitionBase,channel);return kResultTrue;
        case 25:id=voiceParam(kParamVoiceAttackBase,channel);return kResultTrue;
        case 26:id=voiceParam(kParamVoiceTightnessBase,channel);return kResultTrue;
        default:break;
    }
    const int p=stringPartForMidiChannel(channel);
    if(p<0||p>=kPartCount)return kResultFalse;
    // Extra voice channels also accept conventional CC1/CC3 as lane-local shortcuts.
    if(channel>=4){
        if(cc==kCtrlModWheel){id=voiceParam(kParamVoiceDynamicsBase,channel);return kResultTrue;}
        if(cc==3){id=voiceParam(kParamVoiceVibratoBase,channel);return kResultTrue;}
    }
    switch(cc){case kCtrlModWheel:id=partParam(kParamPartDynamicsBase,p);return kResultTrue;case 3:id=partParam(kParamPartVibratoBase,p);return kResultTrue;case kCtrlExpression:id=partParam(kParamPartExpressionBase,p);return kResultTrue;case kCtrlVolume:id=partParam(kParamPartVolumeBase,p);return kResultTrue;case kCtrlPan:id=partParam(kParamPartPanBase,p);return kResultTrue;case kCtrlSustainOnOff:id=partParam(kParamPartSustainBase,p);return kResultTrue;case kCtrlLegatoFootSwOnOff:id=partParam(kParamPartLegatoBase,p);return kResultTrue;case kCtrlEff1Depth:id=partParam(kParamPartRoomBase,p);return kResultTrue;case 20:id=partParam(kParamPartSpeedProfileBase,p);return kResultTrue;case kPitchBend:id=partParam(kParamPartPitchBendBase,p);return kResultTrue;default:break;}return kResultFalse;}

int32 PLUGIN_API Controller::getKeyswitchCount(int32 busIndex, int16 channel) {
    if (busIndex != 0 || channel < 0 || channel >= 16) return 0;
    return kArticulationCount;
}

tresult PLUGIN_API Controller::getKeyswitchInfo(int32 busIndex, int16 channel,
                                                int32 keySwitchIndex, KeyswitchInfo& info) {
    if (busIndex != 0 || channel < 0 || channel >= 16 ||
        keySwitchIndex < 0 || keySwitchIndex >= kArticulationCount) return kResultFalse;
    static const TChar* kLong[kArticulationCount] = {
        STR16("Sustain"), STR16("Legato"), STR16("Portamento"), STR16("Expressive Long"), STR16("Marcato"), STR16("Staccato"),
        STR16("Spiccato"), STR16("Tremolo"), STR16("Pizzicato"), STR16("Trill"), STR16("Harmonic"), STR16("Flautando")
    };
    static const TChar* kShort[kArticulationCount] = {
        STR16("Sus"), STR16("Leg"), STR16("Port"), STR16("Expr"), STR16("Marc"), STR16("Stac"),
        STR16("Spic"), STR16("Trem"), STR16("Pizz"), STR16("Trill"), STR16("Harm"), STR16("Flaut")
    };
    std::memset(&info, 0, sizeof(KeyswitchInfo));
    info.typeId = kNoteOnKeyswitchTypeID;
    Steinberg::UString(info.title, 128).assign(kLong[keySwitchIndex]);
    Steinberg::UString(info.shortTitle, 128).assign(kShort[keySwitchIndex]);
    const int note = kKeyswitchBaseMidi + keySwitchIndex;
    info.keyswitchMin = note;
    info.keyswitchMax = note;
    info.keyRemapped = -1;
    info.unitId = -1;
    info.flags = 0;
    return kResultTrue;
}

tresult PLUGIN_API Controller::setComponentState(IBStream* state){
    if(!state)return kResultFalse;
    IBStreamer s(state,kLittleEndian);int32 version=0;
    if(!s.readInt32(version)||(version<3||version>14))return kResultFalse;
    float mode=0,active=0,human=.16f,mix=0,layout=0,instrumentSel=0,assist=.5f,look=.35f,divisi=0;
    if(!s.readFloat(mode)||!s.readFloat(active)||!s.readFloat(human)||!s.readFloat(mix)||!s.readFloat(layout)||!s.readFloat(instrumentSel)||!s.readFloat(assist)||!s.readFloat(look)||!s.readFloat(divisi))return kResultFalse;
    setParamNormalized(kParamMode,mode);setParamNormalized(kParamActivePart,active);setParamNormalized(kParamHumanize,human);setParamNormalized(kParamAIMix,mix);setParamNormalized(kParamLayoutMode,layout);setParamNormalized(kParamSingleInstrument,instrumentSel);setParamNormalized(kParamAIAssist,assist);setParamNormalized(kParamLookAhead,look);setParamNormalized(kParamAutoDivisi,divisi);
    if(version>=5){
        float x[8]{};for(float&v:x)if(!s.readFloat(v))return kResultFalse;
        setParamNormalized(kParamPerformanceStyle,x[0]);setParamNormalized(kParamSmartDynamics,x[1]);setParamNormalized(kParamSmartArticulation,x[2]);setParamNormalized(kParamRetakeTarget,x[3]);setParamNormalized(kParamRetakeAmount,x[4]);setParamNormalized(kParamRetakeNonce,x[5]);setParamNormalized(kParamStagePerspective,x[6]);setParamNormalized(kParamPolyphony,x[7]);
        if(version>=6){float y[3]{};for(float&v:y)if(!s.readFloat(v))return kResultFalse;setParamNormalized(kParamMidiAuthorityLock,y[0]);setParamNormalized(kParamPhraseDirector,y[1]);setParamNormalized(kParamEnsembleLooseness,y[2]);}
        else{setParamNormalized(kParamMidiAuthorityLock,1);setParamNormalized(kParamPhraseDirector,1);setParamNormalized(kParamEnsembleLooseness,.18);}
        if(version>=7){float z[3]{};for(float&v:z)if(!s.readFloat(v))return kResultFalse;setParamNormalized(kParamHostScopeMode,z[0]);setParamNormalized(kParamHostScopeStyle,z[1]);setParamNormalized(kParamHostScopeLooseness,z[2]);}
        else{setParamNormalized(kParamHostScopeMode,0);setParamNormalized(kParamHostScopeStyle,0);setParamNormalized(kParamHostScopeLooseness,.30);}
        if(version>=8){float q[3]{};for(float&v:q)if(!s.readFloat(v))return kResultFalse;setParamNormalized(kParamTakeCarouselMode,q[0]);setParamNormalized(kParamTakeCarouselSelect,q[1]);setParamNormalized(kParamTakeCarouselFreeze,q[2]);}
        else{setParamNormalized(kParamTakeCarouselMode,0);setParamNormalized(kParamTakeCarouselSelect,0);setParamNormalized(kParamTakeCarouselFreeze,0);}
        if(version>=9){float c[2]{};for(float&v:c)if(!s.readFloat(v))return kResultFalse;setParamNormalized(kParamTakeCompMode,c[0]);setParamNormalized(kParamTakeCompPhraseLength,c[1]);}
        else{setParamNormalized(kParamTakeCompMode,0);setParamNormalized(kParamTakeCompPhraseLength,.25);}
        if(version>=11){
            float mem[2]{};int32 cursorKey=0;
            if(!s.readFloat(mem[0])||!s.readFloat(mem[1])||!s.readInt32(cursorKey))return kResultFalse;
            setParamNormalized(kParamMemoryFollowPlayhead,mem[0]);setParamNormalized(kParamMemoryRecallTake,mem[1]);
        }else{
            setParamNormalized(kParamMemoryFollowPlayhead,1);setParamNormalized(kParamMemoryRecallTake,0);
        }
        if(version>=12){float rank=0;if(!s.readFloat(rank))return kResultFalse;setParamNormalized(kParamSmartRankMode,rank);}
        else setParamNormalized(kParamSmartRankMode,.5);
        if(version>=13){float p13[6]{};for(float&v:p13)if(!s.readFloat(v))return kResultFalse;setParamNormalized(kParamPersonalTasteEnable,p13[0]);setParamNormalized(kParamPersonalTasteStrength,p13[1]);setParamNormalized(kParamPersonalTasteLearn,p13[2]);setParamNormalized(kParamPreferenceMinConfidence,p13[3]);setParamNormalized(kParamPreferenceMinMargin,p13[4]);setParamNormalized(kParamPreferenceSafetyFloor,p13[5]);}
        else {setParamNormalized(kParamPersonalTasteEnable,1);setParamNormalized(kParamPersonalTasteStrength,.75);setParamNormalized(kParamPersonalTasteLearn,1);setParamNormalized(kParamPreferenceMinConfidence,.30);setParamNormalized(kParamPreferenceMinMargin,.10);setParamNormalized(kParamPreferenceSafetyFloor,.35);}
        if(version>=14){float m14[19]{};for(float&v:m14)if(!s.readFloat(v))return kResultFalse;setParamNormalized(kParamStageMixerEnable,m14[0]);setParamNormalized(kParamStageMasterGain,m14[1]);setParamNormalized(kParamStageOutputGain,m14[2]);for(int i=0;i<16;++i)setParamNormalized(kParamStageFeedGainBase+i,m14[3+i]);}
        else {const double d[16]={.25,.35,.25,.45,.62,.45,.28,.28,.20,.20,0.,.12,.12,.06,.06,0.};setParamNormalized(kParamStageMixerEnable,0);setParamNormalized(kParamStageMasterGain,1);setParamNormalized(kParamStageOutputGain,1.);for(int i=0;i<16;++i)setParamNormalized(kParamStageFeedGainBase+i,d[i]);}
        if(version>=10){
            int32 compCount=0;if(!s.readInt32(compCount)||compCount<0||compCount>128)return kResultFalse;
            for(int32 i=0;i<compCount;++i){int32 phrase=0,take=0,fav=0,rej=0,committed=1;
                if(!s.readInt32(phrase)||!s.readInt32(take)||!s.readInt32(fav)||!s.readInt32(rej))return kResultFalse;
                if(version>=11&&!s.readInt32(committed))return kResultFalse;
                if(take<0||take>3||(fav&~0x0F)||(rej&~0x0F)||(committed!=0&&committed!=1))return kResultFalse;
            }
        }
        // Reset transient action/status parameters only. Persistent values read above
        // (Follow Playhead, Recall Take, Smart Rank Mode, etc.) must survive project restore.
        setParamNormalized(kParamTakeCompCommit,0);setParamNormalized(kParamTakeCompClear,0);
        setParamNormalized(kParamTakeCompUndo,0);setParamNormalized(kParamTakeCompRedo,0);
        setParamNormalized(kParamTakeCompFavorite,0);setParamNormalized(kParamTakeCompReject,0);setParamNormalized(kParamTakeCompCommitAll,0);
        setParamNormalized(kParamMemoryPrev,0);setParamNormalized(kParamMemoryNext,0);setParamNormalized(kParamMemoryNextUnresolved,0);
        setParamNormalized(kParamMemoryRecallApply,0);setParamNormalized(kParamMemoryCommitRecall,0);
        setParamNormalized(kParamMemoryFavoriteRecall,0);setParamNormalized(kParamMemoryRejectRecall,0);setParamNormalized(kParamMemoryClearPhrase,0);
        setParamNormalized(kParamMemoryCommittedTake,0);setParamNormalized(kParamMemoryRecallFavorite,0);setParamNormalized(kParamMemoryRecallRejected,0);
        setParamNormalized(kParamMemoryCoverage,0);setParamNormalized(kParamMemoryCursorPosition,0);
        for(int slot=0;slot<8;++slot){setParamNormalized(timelineParam(kParamTimelineCommittedBase,slot),0);setParamNormalized(timelineParam(kParamTimelineSmartPickBase,slot),0);}
        setParamNormalized(kParamSmartAudition,0);setParamNormalized(kParamSmartCommit,0);setParamNormalized(kParamSmartScore,0);
        setParamNormalized(kParamTimelineCursorSlot,0);setParamNormalized(kParamCommitUniqueFavorites,0);setParamNormalized(kParamAutoCompUnresolved,0);
        setParamNormalized(kParamSmartVariation,0);setParamNormalized(kParamTimelineUnresolved,0);
        setParamNormalized(kParamJudgeTrigger,0);setParamNormalized(kParamJudgeWinner,0);
        for(int take=0;take<4;++take){setParamNormalized(judgeParam(kParamJudgeOverallBase,take),0);setParamNormalized(judgeParam(kParamJudgeDynamicsBase,take),0);setParamNormalized(judgeParam(kParamJudgeAttackBase,take),0);setParamNormalized(judgeParam(kParamJudgeTransitionBase,take),0);setParamNormalized(judgeParam(kParamJudgeStabilityBase,take),0);}
        setParamNormalized(kParamJudgeWinnerSafety,0);setParamNormalized(kParamJudgeAuditionWinner,0);setParamNormalized(kParamJudgeCommitWinner,0);
        setParamNormalized(kParamPersonalTasteClear,0);setParamNormalized(kParamPersonalConfidence,0);setParamNormalized(kParamPersonalEvidence,0);for(int i=0;i<5;++i)setParamNormalized(personalParam(kParamPersonalWeightBase,i),.5);for(int i=0;i<4;++i)setParamNormalized(personalParam(kParamPersonalScoreBase,i),0);
        setParamNormalized(kParamPreferenceAutoComp,0);setParamNormalized(kParamPreferenceAutoCompCancel,0);setParamNormalized(kParamPreferenceAutoCompStatus,0);setParamNormalized(kParamPreferenceAutoCompProgress,0);setParamNormalized(kParamPreferenceAutoCompCommitted,0);setParamNormalized(kParamPreferenceAutoCompReview,0);
    }else{
        setParamNormalized(kParamPerformanceStyle,0);setParamNormalized(kParamSmartDynamics,0);setParamNormalized(kParamSmartArticulation,0);
        setParamNormalized(kParamRetakeTarget,0);setParamNormalized(kParamRetakeAmount,0);setParamNormalized(kParamRetakeNonce,0);
        setParamNormalized(kParamStagePerspective,1.0/3.0);setParamNormalized(kParamPolyphony,1);
        setParamNormalized(kParamMidiAuthorityLock,1);setParamNormalized(kParamPhraseDirector,1);setParamNormalized(kParamEnsembleLooseness,.18);
        setParamNormalized(kParamHostScopeMode,0);setParamNormalized(kParamHostScopeStyle,0);setParamNormalized(kParamHostScopeLooseness,.30);
        setParamNormalized(kParamTakeCarouselMode,0);setParamNormalized(kParamTakeCarouselSelect,0);setParamNormalized(kParamTakeCarouselFreeze,0);
        setParamNormalized(kParamTakeCompMode,0);setParamNormalized(kParamTakeCompPhraseLength,.25);
        setParamNormalized(kParamMemoryFollowPlayhead,1);setParamNormalized(kParamMemoryRecallTake,0);setParamNormalized(kParamSmartRankMode,.5);
        setParamNormalized(kParamTakeCompCommit,0);setParamNormalized(kParamTakeCompClear,0);setParamNormalized(kParamTakeCompUndo,0);setParamNormalized(kParamTakeCompRedo,0);
        setParamNormalized(kParamTakeCompFavorite,0);setParamNormalized(kParamTakeCompReject,0);setParamNormalized(kParamTakeCompCommitAll,0);
        setParamNormalized(kParamMemoryPrev,0);setParamNormalized(kParamMemoryNext,0);setParamNormalized(kParamMemoryNextUnresolved,0);
        setParamNormalized(kParamMemoryRecallApply,0);setParamNormalized(kParamMemoryCommitRecall,0);setParamNormalized(kParamMemoryFavoriteRecall,0);setParamNormalized(kParamMemoryRejectRecall,0);setParamNormalized(kParamMemoryClearPhrase,0);
        setParamNormalized(kParamMemoryCommittedTake,0);setParamNormalized(kParamMemoryRecallFavorite,0);setParamNormalized(kParamMemoryRecallRejected,0);setParamNormalized(kParamMemoryCoverage,0);setParamNormalized(kParamMemoryCursorPosition,0);
        for(int slot=0;slot<8;++slot){setParamNormalized(timelineParam(kParamTimelineCommittedBase,slot),0);setParamNormalized(timelineParam(kParamTimelineSmartPickBase,slot),0);}
        setParamNormalized(kParamSmartAudition,0);setParamNormalized(kParamSmartCommit,0);setParamNormalized(kParamSmartScore,0);setParamNormalized(kParamTimelineCursorSlot,0);
        setParamNormalized(kParamCommitUniqueFavorites,0);setParamNormalized(kParamAutoCompUnresolved,0);setParamNormalized(kParamSmartVariation,0);setParamNormalized(kParamTimelineUnresolved,0);
        setParamNormalized(kParamJudgeTrigger,0);setParamNormalized(kParamJudgeWinner,0);
        for(int take=0;take<4;++take){setParamNormalized(judgeParam(kParamJudgeOverallBase,take),0);setParamNormalized(judgeParam(kParamJudgeDynamicsBase,take),0);setParamNormalized(judgeParam(kParamJudgeAttackBase,take),0);setParamNormalized(judgeParam(kParamJudgeTransitionBase,take),0);setParamNormalized(judgeParam(kParamJudgeStabilityBase,take),0);}
        setParamNormalized(kParamJudgeWinnerSafety,0);setParamNormalized(kParamJudgeAuditionWinner,0);setParamNormalized(kParamJudgeCommitWinner,0);
        setParamNormalized(kParamPersonalTasteClear,0);setParamNormalized(kParamPersonalConfidence,0);setParamNormalized(kParamPersonalEvidence,0);for(int i=0;i<5;++i)setParamNormalized(personalParam(kParamPersonalWeightBase,i),.5);for(int i=0;i<4;++i)setParamNormalized(personalParam(kParamPersonalScoreBase,i),0);
        setParamNormalized(kParamPreferenceAutoComp,0);setParamNormalized(kParamPreferenceAutoCompCancel,0);setParamNormalized(kParamPreferenceAutoCompStatus,0);setParamNormalized(kParamPreferenceAutoCompProgress,0);setParamNormalized(kParamPreferenceAutoCompCommitted,0);setParamNormalized(kParamPreferenceAutoCompReview,0);
    }
    for(int p=0;p<kPartCount;++p){float vals[14]{};for(int i=0;i<13;++i)if(!s.readFloat(vals[i]))return kResultFalse;if(version>=4){if(!s.readFloat(vals[13]))return kResultFalse;}setParamNormalized(partParam(kParamPartDynamicsBase,p),vals[0]);setParamNormalized(partParam(kParamPartVibratoBase,p),vals[1]);setParamNormalized(partParam(kParamPartExpressionBase,p),vals[2]);setParamNormalized(partParam(kParamPartVolumeBase,p),vals[3]);setParamNormalized(partParam(kParamPartPanBase,p),vals[4]);setParamNormalized(partParam(kParamPartSustainBase,p),vals[5]);setParamNormalized(partParam(kParamPartLegatoBase,p),vals[6]);setParamNormalized(partParam(kParamPartRoomBase,p),vals[7]);setParamNormalized(partParam(kParamPartPitchBendBase,p),vals[8]);setParamNormalized(partParam(kParamPartArticulationBase,p),vals[9]);setParamNormalized(partParam(kParamPartTransitionSpeedBase,p),vals[10]);setParamNormalized(partParam(kParamPartShortTightnessBase,p),vals[11]);setParamNormalized(partParam(kParamPartAttackCharacterBase,p),vals[12]);setParamNormalized(partParam(kParamPartSpeedProfileBase,p),vals[13]);}
    return kResultOk;
}
}
