#include "processor.h"
#include "controller.h"
#include "ids.h"
#include "articulations.h"
#include "pluginterfaces/vst/ivstevents.h"
#include "base/source/fstreamer.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>

using namespace Steinberg;
using namespace Steinberg::Vst;

namespace Sonicraft::AIStrings {
namespace {

constexpr int kStateVersion = 14;
constexpr int kAuxFeedCount = 16;
constexpr std::size_t kMaxAutomationPointsPerBlock = 4096;

struct AutomationPoint {
    int32 sampleOffset {0};
    ParamID id {0};
    float value {0.f};
};

int artFromNormalized(float v) noexcept {
    return std::clamp(static_cast<int>(v * static_cast<float>(kArticulationCount - 1) + .5f),
                      0, kArticulationCount - 1);
}

bool decodeGestureVoiceParam(ParamID id, int& channel, ParamID& base) noexcept {
    if(id>=kParamVoiceGestureAmountBase && id<kParamVoiceGestureAmountBase+16){
        channel=static_cast<int>(id-kParamVoiceGestureAmountBase);base=kParamVoiceGestureAmountBase;return true;
    }
    return false;
}

bool decodeEnsembleVoiceParam(ParamID id, int& channel, ParamID& base) noexcept {
    constexpr ParamID bases[] = {kParamVoiceEnsembleAttackBase,kParamVoicePhraseBreathBase};
    for(auto b:bases){
        if(id>=b && id<b+16){channel=static_cast<int>(id-b);base=b;return true;}
    }
    return false;
}

bool decodePhysicalVoiceParam(ParamID id, int& channel, ParamID& base) noexcept {
    constexpr ParamID bases[] = {
        kParamVoiceStringBase,kParamVoicePositionBase,kParamVoiceBowDirectionBase,kParamVoiceBowChangeBase,
        kParamVoiceBowPressureBase,kParamVoiceContactPointBase,kParamVoicePortamentoBase,kParamVoiceDeskBase
    };
    for(auto b:bases){
        if(id>=b && id<b+16){channel=static_cast<int>(id-b);base=b;return true;}
    }
    return false;
}

bool decodeVoiceParam(ParamID id, int& channel, ParamID& base) noexcept {
    constexpr ParamID bases[] = {
        kParamVoiceStackBase,kParamVoiceDynamicsBase,kParamVoiceVibratoBase,
        kParamVoiceTransitionBase,kParamVoiceAttackBase,kParamVoiceTightnessBase,kParamVoiceMicroPitchBase
    };
    for(auto b:bases){
        if(id>=b && id<b+16){channel=static_cast<int>(id-b);base=b;return true;}
    }
    return false;
}

bool decodePartParam(ParamID id, int& p, ParamID& base) noexcept {
    constexpr ParamID bases[] = {
        kParamPartDynamicsBase, kParamPartVibratoBase, kParamPartExpressionBase,
        kParamPartVolumeBase, kParamPartPanBase, kParamPartSustainBase,
        kParamPartLegatoBase, kParamPartRoomBase, kParamPartPitchBendBase,
        kParamPartArticulationBase, kParamPartTransitionSpeedBase,
        kParamPartShortTightnessBase, kParamPartAttackCharacterBase,
        kParamPartSpeedProfileBase
    };
    for (auto b : bases) {
        if (id >= b && id < b + static_cast<ParamID>(kPartCount)) {
            p = static_cast<int>(id - b);
            base = b;
            return true;
        }
    }
    return false;
}

PartControl toPreviewControl(const Processor::Controls& c) noexcept {
    PartControl pc{};
    pc.dynamics=c.dyn;pc.vibrato=c.vib;pc.expression=c.exp;pc.volume=c.vol;pc.pan=c.pan;pc.room=c.room;pc.pitchBend=c.bend;
    pc.sustain=c.sus>=.5f;pc.legato=c.leg>=.5f;pc.articulation=artFromNormalized(c.art);
    pc.transitionSpeed=c.transition;pc.shortTightness=c.tightness;pc.attackCharacter=c.attack;pc.speedProfile=c.speedProfile;
    return pc;
}

ShadowControls toShadow(const Processor::Controls& c) noexcept {
    ShadowControls sc {};
    sc.dyn = c.dyn; sc.vib = c.vib; sc.exp = c.exp; sc.vol = c.vol;
    sc.pan = c.pan; sc.sus = c.sus; sc.leg = c.leg; sc.room = c.room;
    sc.bend = c.bend; sc.art = c.art; sc.transition = c.transition;
    sc.tightness = c.tightness; sc.attack = c.attack; sc.speedProfile = c.speedProfile;
    return sc;
}

} // namespace

Processor::Processor() { setControllerClass(kControllerUID); }

tresult PLUGIN_API Processor::initialize(FUnknown* context) {
    const auto r = AudioEffect::initialize(context);
    if (r != kResultOk) return r;
    addEventInput(STR16("Q4 MIDI In"), 16);
    addAudioOutput(STR16("Q4 Master"), SpeakerArr::kStereo, kMain, BusInfo::kDefaultActive);
    addAudioOutput(STR16("Spot L"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Spot C"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Spot R"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Tree L"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Tree C"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Tree R"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Wide L"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Wide R"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Room L"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Room R"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Rear"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Mid L"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Mid R"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Far L"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Far R"), SpeakerArr::kStereo, kAux, 0);
    addAudioOutput(STR16("Gallery"), SpeakerArr::kStereo, kAux, 0);
    return kResultOk;
}

int Processor::chooseDivisiPart(int note) const noexcept {
    // Register-aware assignment with light load balancing. Existing authored Q4 channels remain untouched;
    // this path is only used for single-source channel 1 when Auto Divisi is explicitly enabled.
    const int preferred = note <= 52 ? 3 : (note <= 60 ? 2 : (note <= 67 ? 1 : 0));
    int best = preferred;
    int bestCost = divisiActive[best] * 5;
    static constexpr int center[4] = {76,67,60,48};
    for (int p=0;p<4;++p) {
        const int rangePenalty = std::abs(note-center[p]) / 5;
        const int crossingPenalty = (p < preferred ? 2 : 0);
        const int cost = divisiActive[p]*5 + rangePenalty + crossingPenalty;
        if (cost < bestCost) { best=p; bestCost=cost; }
    }
    return best;
}

tresult PLUGIN_API Processor::setBusArrangements(SpeakerArrangement*, int32 numIns,
                                                  SpeakerArrangement* outputs, int32 numOuts) {
    if (numIns != 0 || !outputs || numOuts < 1 || numOuts > 1 + kAuxFeedCount) return kResultFalse;
    for (int32 i = 0; i < numOuts; ++i) if (outputs[i] != SpeakerArr::kStereo) return kResultFalse;
    return AudioEffect::setBusArrangements(nullptr, 0, outputs, numOuts);
}

tresult PLUGIN_API Processor::setupProcessing(ProcessSetup& setup) {
    engine.setSampleRate(setup.sampleRate);
    shadow.configure(setup.sampleRate);
    return AudioEffect::setupProcessing(setup);
}

Steinberg::uint32 PLUGIN_API Processor::getProcessContextRequirements() {
    return IProcessContextRequirements::kNeedTempo |
           IProcessContextRequirements::kNeedProjectTimeMusic |
           IProcessContextRequirements::kNeedCycleMusic |
           IProcessContextRequirements::kNeedTransportState;
}

tresult PLUGIN_API Processor::canProcessSampleSize(int32 s) {
    return s == kSample32 ? kResultTrue : kResultFalse;
}

tresult PLUGIN_API Processor::process(ProcessData& data) {
    const int64_t projectStart = data.processContext ? data.processContext->projectTimeSamples : lastProjectEnd;
    const bool isPlaying = data.processContext && ((data.processContext->state & ProcessContext::kPlaying) != 0);
    const bool cycleActive = data.processContext && ((data.processContext->state & ProcessContext::kCycleActive) != 0);

    HostCycleWindow hostWindow{};
    double blockStartQuarter = 0.0;
    bool blockQuarterValid = false;
    if (data.processContext) {
        if (data.processContext->state & ProcessContext::kProjectTimeMusicValid) {
            blockStartQuarter = data.processContext->projectTimeMusic;
            blockQuarterValid = std::isfinite(blockStartQuarter);
        }
        if ((data.processContext->state & ProcessContext::kCycleValid) &&
            std::isfinite(data.processContext->cycleStartMusic) &&
            std::isfinite(data.processContext->cycleEndMusic) &&
            data.processContext->cycleEndMusic > data.processContext->cycleStartMusic) {
            hostWindow = {true, data.processContext->cycleStartMusic, data.processContext->cycleEndMusic};
        }
    }

    if (lastProjectEnd != 0 &&
        (projectStart < lastProjectEnd - data.numSamples || projectStart > lastProjectEnd + data.numSamples * 4LL)) {
        shadow.resetTimeline(projectStart);
    }
    lastProjectEnd = projectStart + data.numSamples;

    if (data.processContext && (data.processContext->state & ProcessContext::kTempoValid)) {
        hostTempoBpm = data.processContext->tempo;
        engine.setTempo(hostTempoBpm);
        if (data.processContext->state & ProcessContext::kProjectTimeMusicValid)
            tempoTimeline.observe(data.processContext->projectTimeMusic, hostTempoBpm, projectStart);
    }

    auto syncPartToEngine = [&](int p) noexcept {
        const auto& c = part[p];
        engine.setPartDynamics(p, c.dyn);
        engine.setPartVibrato(p, c.vib);
        engine.setPartExpression(p, c.exp);
        engine.setPartVolume(p, c.vol);
        engine.setPartPan(p, c.pan);
        engine.setPartSustain(p, c.sus >= .5f);
        engine.setPartLegato(p, c.leg >= .5f);
        engine.setPartRoom(p, c.room);
        engine.setPartPitchBend(p, c.bend);
        engine.setPartArticulation(p, artFromNormalized(c.art));
        engine.setPartTransitionSpeed(p, c.transition);
        engine.setPartShortTightness(p, c.tightness);
        engine.setPartAttackCharacter(p, c.attack);
        engine.setPartSpeedProfile(p, c.speedProfile);
    };

    auto mergedVoiceControl = [&](int lane) noexcept -> Controls {
        const int p=stringPartForMidiChannel(lane);
        Controls c=(p>=0&&p<kPartCount)?part[p]:Controls{};
        const auto& o=voiceLane[std::clamp(lane,0,15)];
        if(o.mask&0x01)c.stack=o.stack;
        if(o.mask&0x02)c.dyn=o.dyn;
        if(o.mask&0x04)c.vib=o.vib;
        if(o.mask&0x08)c.transition=o.transition;
        if(o.mask&0x10)c.attack=o.attack;
        if(o.mask&0x20)c.tightness=o.tightness;
        if(o.mask&0x40)c.art=o.art;
        if(o.mask&0x80)c.bend=o.bend;
        c=applyStringExpressionModifiers(c,expressionStackFromNormalized(c.stack));
        if(o.physicalMask)c=applyStringPhysicalResidualsV42(c,o.physical,o.physicalMask);
        if(o.ensembleMask)c=applyStringEnsemblePreviewResidualsV44(c,o.ensemble,o.ensembleMask);
        return c;
    };

    auto previewVoiceControl = [&](int lane,const Controls& c) noexcept -> PartControl {
        auto pc=toPreviewControl(c);
        const auto& o=voiceLane[std::clamp(lane,0,15)];
        pc.continuousGesture=o.gestureAmount>.0001f;
        if(o.mask&0x80)pc.pitchBend=previewGesturePitchBendV46(o.bend,o.gestureAmount);
        return pc;
    };

    // State restoration can happen without automation points in the first process block.
    // Synchronize the DSP engine from persistent parameter state before applying this block's points.
    engine.setHumanize(humanize);
    for (int p = 0; p < kPartCount; ++p) syncPartToEngine(p);

    const int carouselModeIndexAtBlockStart = std::clamp(static_cast<int>(takeCarouselMode * 2.f + .5f), 0, 2);
    const int carouselSelectedAtBlockStart = takeIndexFromNormalized(takeCarouselSelect);
    const bool carouselFrozenAtBlockStart = takeCarouselFreeze >= .5f;
    takeCarouselTracker.update(carouselModeIndexAtBlockStart, carouselSelectedAtBlockStart,
                               carouselFrozenAtBlockStart, isPlaying && cycleActive, blockQuarterValid,
                               blockStartQuarter, hostWindow);

    const bool multiOutActive = data.numOutputs > 1;
    auto quarterAtOffset = [&](int32 sampleOffset) noexcept -> double {
        if (!blockQuarterValid) return 0.0;
        const double sr = data.processContext ? data.processContext->sampleRate : 48000.0;
        if (!(sr > 0.0) || !(hostTempoBpm > 0.0)) return blockStartQuarter;
        return blockStartQuarter + (static_cast<double>(sampleOffset) / sr) * (hostTempoBpm / 60.0);
    };
    auto memoryPhraseLengthQuarter = [&]() noexcept -> double {
        return 1.0 + std::clamp(static_cast<double>(takeCompPhraseLength),0.0,1.0) * 15.0;
    };
    auto memoryWindow = [&]() noexcept -> PerformanceMemoryWindow {
        return memoryWindowFromQuarters(hostWindow.valid, hostWindow.startQuarter, hostWindow.endQuarter,
                                        memoryPhraseLengthQuarter());
    };
    auto memoryPhraseCenterQuarter = [&]() noexcept -> double {
        return (static_cast<double>(memoryCursorKey)+.5)*memoryPhraseLengthQuarter();
    };
    auto memoryPhraseSampleRange = [&]() noexcept -> std::array<int64_t,2> {
        if(!data.processContext)return {{0,0}};
        const double sr=data.processContext->sampleRate;if(!(sr>0.0))return {{0,0}};
        const double len=memoryPhraseLengthQuarter();const double q0=static_cast<double>(memoryCursorKey)*len,q1=q0+len;
        int64_t s0=0,s1=0;
        if(tempoTimeline.sampleAtBeat(q0,sr,s0)&&tempoTimeline.sampleAtBeat(q1,sr,s1)&&s1>s0)return {{s0,s1}};
        if(!blockQuarterValid||!(hostTempoBpm>0.0))return {{0,0}};
        const double spq=sr*60.0/hostTempoBpm;
        s0=projectStart+static_cast<int64_t>(std::llround((q0-blockStartQuarter)*spq));
        s1=projectStart+static_cast<int64_t>(std::llround((q1-blockStartQuarter)*spq));return {{s0,s1}};
    };
    auto judgeScopedState = [&]() noexcept -> ScopedPerformanceState {
        const int scopeModeIndex=std::clamp(static_cast<int>(hostScopeMode*3.f+.5f),0,3);
        const double center=memoryPhraseCenterQuarter();const bool inside=hostWindow.valid&&hostScopeInside(center,hostWindow);
        return resolveHostScope(hostWindow.valid?scopeModeIndex:kHostScopeOff,inside,performanceStyle,retakeTarget,retakeAmount,retakeNonce,
                                phraseDirector,ensembleLooseness,hostScopeStyle,hostScopeLooseness);
    };
    auto judgePhraseTempo = [&]() noexcept -> float {return static_cast<float>(tempoTimeline.tempoAtBeat(memoryPhraseCenterQuarter(),hostTempoBpm));};
    auto judgePolicyFlags = [&](const ScopedPerformanceState& s) noexcept -> uint32_t {
        return (uint32_t(std::clamp(int(std::round(aiAssist*2.f)),0,2))&0x3u) |
               ((uint32_t(std::clamp(int(std::round(s.performanceStyle*5.f)),0,5))&0x7u)<<2) |
               (uint32_t(smartDynamics>=.5f)<<5)|(uint32_t(smartArticulation>=.5f)<<6)|(uint32_t(polyphony>=.5f)<<7) |
               ((uint32_t(std::clamp(int(std::round(s.retakeTarget*7.f)),0,7))&0x7u)<<8) |
               ((uint32_t(std::clamp(int(std::round(s.retakeNonce*255.f)),0,255))&0xFFu)<<11) |
               ((uint32_t(std::clamp(int(std::round(stagePerspective*3.f)),0,3))&0x3u)<<19) |
               ((uint32_t(std::clamp(int(std::round(s.retakeAmount*15.f)),0,15))&0xFu)<<21) |
               (uint32_t(multiOutActive)<<25)|(uint32_t(midiAuthorityLock>=.5f)<<26)|(uint32_t(s.phraseDirector>=.5f)<<27) |
               ((uint32_t(std::clamp(int(std::round(s.ensembleLooseness*15.f)),0,15))&0xFu)<<28);
    };
    auto judgeConfigToken = [&](uint8_t favoriteMask,uint8_t rejectMask,const ScopedPerformanceState& s,float phraseTempo) noexcept -> uint64_t {
        uint64_t h=1469598103934665603ull;
        auto add=[&](uint64_t v) noexcept {for(int i=0;i<8;++i){h^=uint8_t(v&0xFFu);h*=1099511628211ull;v>>=8;}};
        auto q=[&](float v,int scale) noexcept -> uint64_t {return uint64_t(std::clamp(int(std::llround(double(std::clamp(v,0.f,1.f))*scale)),0,scale));};
        add(q(s.retakeNonce,16777215));add(q(s.retakeAmount,4095));add(q(s.retakeTarget,7));add(q(aiAssist,2));add(q(s.performanceStyle,5));
        add(smartDynamics>=.5f);add(smartArticulation>=.5f);add(midiAuthorityLock>=.5f);add(s.phraseDirector>=.5f);add(q(s.ensembleLooseness,4095));
        add(q(stagePerspective,3));add(polyphony>=.5f);add(q(mode,2));add(q(lookAhead,4095));add(multiOutActive);
        add(q(layoutMode,1));add(q(singleInstrument,3));add(autoDivisi>=.5f);
        add(uint64_t(std::llround(std::clamp(phraseTempo,20.f,400.f)*100.f)));
        add(uint64_t(favoriteMask&0x0F));add(uint64_t(rejectMask&0x0F));
        for(const auto& c:part){for(float v:{c.dyn,c.vib,c.exp,c.vol,c.pan,c.sus,c.leg,c.room,c.bend,c.art,c.transition,c.tightness,c.attack,c.speedProfile})add(q(v,4095));}
        for(const auto& o:voiceLane){
            add(o.mask);add(o.physicalMask);add(o.ensembleMask);add(q(o.gestureAmount,4095));
            for(float v:{o.stack,o.dyn,o.vib,o.transition,o.attack,o.tightness,o.art,o.bend,
                         o.physical.stringIndex,o.physical.position,o.physical.bowDirection,o.physical.bowChange,
                         o.physical.bowPressure,o.physical.contactPoint,o.physical.portamento,o.physical.desk,
                         o.ensemble.attackOffset,o.ensemble.phraseBreath})add(q(v,4095));
        }
        return h;
    };
    auto personalProfile = [&]() noexcept { return preference.snapshot(); };
    auto judgeMatchesCurrentProfile = [&](const TakeJudgeSnapshotV37& snap) noexcept -> bool {
        if(personalTasteEnable<.5f)return true; const auto p=personalProfile();
        return snap.profileHash32!=0 && snap.profileHash32==static_cast<uint32_t>(p.hash&0xFFFFFFFFu);
    };
    auto syncMemoryCursor = [&](int32 sampleOffset) noexcept {
        if(memoryFollowPlayhead >= .5f && blockQuarterValid)
            memoryCursorKey = phraseKeyFromQuarterV34(quarterAtOffset(sampleOffset), memoryPhraseLengthQuarter());
        else
            memoryCursorKey = clampMemoryCursor(memoryCursorKey, memoryWindow());
    };
    syncMemoryCursor(0);
    auto runtimeState = [&](int32 sampleOffset) noexcept {
        const int modeIndex = std::clamp(static_cast<int>(mode * 2.f + .5f), 0, 2);
        const int scopeModeIndex = std::clamp(static_cast<int>(hostScopeMode * 3.f + .5f), 0, 3);
        const bool scopeUsable = hostWindow.valid && blockQuarterValid;
        const bool inside = scopeUsable && hostScopeInside(quarterAtOffset(sampleOffset), hostWindow);
        auto scoped = resolveHostScope(scopeUsable ? scopeModeIndex : kHostScopeOff, inside,
                                     performanceStyle, retakeTarget, retakeAmount, retakeNonce,
                                     phraseDirector, ensembleLooseness,
                                     hostScopeStyle, hostScopeLooseness);
        const int carouselModeIndex = std::clamp(static_cast<int>(takeCarouselMode * 2.f + .5f), 0, 2);
        const int manualTake = takeIndexFromNormalized(takeCarouselSelect);
        int auditionTake = carouselModeIndex == kTakeCarouselManual ? manualTake : takeCarouselTracker.activeTake();
        const int compModeIndex = std::clamp(static_cast<int>(takeCompMode + .5f), 0, 1);
        const double phraseLengthQuarter = 1.0 + std::clamp(static_cast<double>(takeCompPhraseLength),0.0,1.0) * 15.0;
        const int resolvedTake = resolvePersistentCompTake(phraseTakeComp, compModeIndex, inside,
                                                 quarterAtOffset(sampleOffset), phraseLengthQuarter, auditionTake);
        if (carouselModeIndex != kTakeCarouselOff && hostScopeIncludesRetake(scopeModeIndex) && inside)
            scoped.retakeNonce = deriveTakeNonce(scoped.retakeNonce, resolvedTake);
        shadow.setRuntimeState(modeIndex, aiMix, lookAhead, aiAssist, scoped.performanceStyle, smartDynamics, smartArticulation, scoped.retakeTarget, scoped.retakeAmount, scoped.retakeNonce, stagePerspective, polyphony, midiAuthorityLock, scoped.phraseDirector, scoped.ensembleLooseness, multiOutActive, isPlaying,
                               projectStart + sampleOffset,
                               std::max<int32>(0, data.numSamples - sampleOffset),
                               static_cast<float>(hostTempoBpm));
    };
    runtimeState(0);

    // Host locator/cycle boundaries are injected into the same block timeline as automation and
    // MIDI. This avoids waiting for the next block before a scoped Retake/Director switches state.
    std::array<int32,2> scopeBoundaries{{-1,-1}};
    std::size_t scopeBoundaryCount = 0;
    if (hostWindow.valid && blockQuarterValid && data.processContext) {
        const double sr = data.processContext->sampleRate;
        const int a = boundarySampleOffset(blockStartQuarter, hostWindow.startQuarter, hostTempoBpm, sr, data.numSamples);
        const int b = boundarySampleOffset(blockStartQuarter, hostWindow.endQuarter, hostTempoBpm, sr, data.numSamples);
        if (a > 0) scopeBoundaries[scopeBoundaryCount++] = a;
        if (b > 0 && b != a) scopeBoundaries[scopeBoundaryCount++] = b;
        if (scopeBoundaryCount == 2 && scopeBoundaries[1] < scopeBoundaries[0]) std::swap(scopeBoundaries[0],scopeBoundaries[1]);
    }

    auto emitOutputParam = [&](ParamID id, float value) noexcept {
        if(!data.outputParameterChanges) return;
        int32 queueIndex=0;
        auto* queue=data.outputParameterChanges->addParameterData(id,queueIndex);
        if(!queue) return;
        int32 pointIndex=0;
        queue->addPoint(0,static_cast<ParamValue>(std::clamp(value,0.f,1.f)),pointIndex);
    };

    auto learnPreference = [&](int kind,int take) noexcept {
        if(personalTasteLearn<.5f||take<0||take>3)return; const auto snap=shadow.takeJudgeSnapshot();const auto range=memoryPhraseSampleRange();
        PersistentTakeCompEntry e{};uint8_t fav=0,rej=0;if(phraseTakeComp.query(memoryCursorKey,e)){fav=e.favoriteMask;rej=e.rejectMask;}
        const auto scoped=judgeScopedState();const float tempo=judgePhraseTempo();const uint8_t bit=uint8_t(1u<<take);bool tokenMatch=snap.configToken==judgeConfigToken(fav,rej,scoped,tempo);
        if(kind==1){const uint8_t oldFav=uint8_t(fav&~bit);tokenMatch=tokenMatch||snap.configToken==judgeConfigToken(oldFav,rej,scoped,tempo)||snap.configToken==judgeConfigToken(oldFav,uint8_t(rej|bit),scoped,tempo);}
        if(kind==2){const uint8_t oldRej=uint8_t(rej&~bit);tokenMatch=tokenMatch||snap.configToken==judgeConfigToken(fav,oldRej,scoped,tempo)||snap.configToken==judgeConfigToken(uint8_t(fav|bit),oldRej,scoped,tempo);}
        if(range[1]>range[0]&&snap.startSample==range[0]&&tokenMatch) preference.record(kind,take,snap);
    };

    auto applyParameter = [&](ParamID id, float v, int32 offset) noexcept {
        v = std::clamp(v, 0.f, 1.f);
        int gestureLane=-1; ParamID gestureBase=0;
        if(decodeGestureVoiceParam(id,gestureLane,gestureBase)){
            auto& o=voiceLane[gestureLane];o.gestureAmount=v;
            const int vp=stringPartForMidiChannel(gestureLane);
            if(vp>=0){
                const auto c=mergedVoiceControl(gestureLane);
                const int packed=packArticulationExpression(artFromNormalized(c.art),expressionStackFromNormalized(c.stack));
                shadow.pushMidi(ShadowRenderClient::Control,projectStart+offset,encodeShadowStringPart(vp,gestureLane),
                                kGestureAmount,packed,v,static_cast<float>(hostTempoBpm),toShadow(c));
            }
            return;
        }
        int ensembleLane=-1; ParamID ensembleBase=0;
        if(decodeEnsembleVoiceParam(id,ensembleLane,ensembleBase)){
            auto& o=voiceLane[ensembleLane];
            std::uint8_t opcode=0;
            switch(ensembleBase){
                case kParamVoiceEnsembleAttackBase:o.ensemble.attackOffset=v;o.ensembleMask|=0x01;opcode=kEnsembleAttackOffset;break;
                case kParamVoicePhraseBreathBase:o.ensemble.phraseBreath=v;o.ensembleMask|=0x02;opcode=kEnsemblePhraseBreath;break;
                default:break;
            }
            const int vp=stringPartForMidiChannel(ensembleLane);
            if(vp>=0){
                const auto c=mergedVoiceControl(ensembleLane);
                engine.updateVoiceLaneControl(ensembleLane,previewVoiceControl(ensembleLane,c));
                const int packed=packArticulationExpression(artFromNormalized(c.art),expressionStackFromNormalized(c.stack));
                shadow.pushMidi(ShadowRenderClient::Control,projectStart+offset,encodeShadowStringPart(vp,ensembleLane),
                                opcode,packed,v,static_cast<float>(hostTempoBpm),toShadow(c));
            }
            return;
        }
        int physicalLane=-1; ParamID physicalBase=0;
        if(decodePhysicalVoiceParam(id,physicalLane,physicalBase)){
            auto& o=voiceLane[physicalLane];
            std::uint8_t opcode=0;
            switch(physicalBase){
                case kParamVoiceStringBase:o.physical.stringIndex=v;o.physicalMask|=0x01;opcode=kPhysString;break;
                case kParamVoicePositionBase:o.physical.position=v;o.physicalMask|=0x02;opcode=kPhysPosition;break;
                case kParamVoiceBowDirectionBase:o.physical.bowDirection=v;o.physicalMask|=0x04;opcode=kPhysBowDirection;break;
                case kParamVoiceBowChangeBase:o.physical.bowChange=v;o.physicalMask|=0x08;opcode=kPhysBowChange;break;
                case kParamVoiceBowPressureBase:o.physical.bowPressure=v;o.physicalMask|=0x10;opcode=kPhysBowPressure;break;
                case kParamVoiceContactPointBase:o.physical.contactPoint=v;o.physicalMask|=0x20;opcode=kPhysContactPoint;break;
                case kParamVoicePortamentoBase:o.physical.portamento=v;o.physicalMask|=0x40;opcode=kPhysPortamento;break;
                case kParamVoiceDeskBase:o.physical.desk=v;o.physicalMask|=0x80;opcode=kPhysDesk;break;
                default:break;
            }
            const int vp=stringPartForMidiChannel(physicalLane);
            if(vp>=0){
                const auto c=mergedVoiceControl(physicalLane);
                engine.updateVoiceLaneControl(physicalLane,previewVoiceControl(physicalLane,c));
                const int packed=packArticulationExpression(artFromNormalized(c.art),expressionStackFromNormalized(c.stack));
                shadow.pushMidi(ShadowRenderClient::Control,projectStart+offset,encodeShadowStringPart(vp,physicalLane),opcode,packed,v,
                                static_cast<float>(hostTempoBpm),toShadow(c));
            }
            return;
        }
        int lane=-1; ParamID voiceBase=0;
        if(decodeVoiceParam(id,lane,voiceBase)){
            auto& o=voiceLane[lane];
            switch(voiceBase){
                case kParamVoiceStackBase:o.stack=v;o.mask|=0x01;break;
                case kParamVoiceDynamicsBase:o.dyn=v;o.mask|=0x02;break;
                case kParamVoiceVibratoBase:o.vib=v;o.mask|=0x04;break;
                case kParamVoiceTransitionBase:o.transition=v;o.mask|=0x08;break;
                case kParamVoiceAttackBase:o.attack=v;o.mask|=0x10;break;
                case kParamVoiceTightnessBase:o.tightness=v;o.mask|=0x20;break;
                case kParamVoiceMicroPitchBase:o.bend=v;o.mask|=0x80;break;
                default:break;
            }
            const int vp=stringPartForMidiChannel(lane);
            if(vp>=0){
                const auto c=mergedVoiceControl(lane);
                engine.updateVoiceLaneControl(lane,previewVoiceControl(lane,c));
                const int packed=packArticulationExpression(artFromNormalized(c.art),expressionStackFromNormalized(c.stack));
                shadow.pushMidi(ShadowRenderClient::Control,projectStart+offset,encodeShadowStringPart(vp,lane),0,packed,0.f,
                                static_cast<float>(hostTempoBpm),toShadow(c));
            }
            return;
        }
        int p = -1; ParamID base = 0;
        if (decodePartParam(id, p, base)) {
            auto& c = part[p];
            switch (base) {
                case kParamPartDynamicsBase: c.dyn = v; engine.setPartDynamics(p, v); break;
                case kParamPartVibratoBase: c.vib = v; engine.setPartVibrato(p, v); break;
                case kParamPartExpressionBase: c.exp = v; engine.setPartExpression(p, v); break;
                case kParamPartVolumeBase: c.vol = v; engine.setPartVolume(p, v); break;
                case kParamPartPanBase: c.pan = v; engine.setPartPan(p, v); break;
                case kParamPartSustainBase: c.sus = v; engine.setPartSustain(p, v >= .5f); break;
                case kParamPartLegatoBase: c.leg = v; engine.setPartLegato(p, v >= .5f); break;
                case kParamPartRoomBase: c.room = v; engine.setPartRoom(p, v); break;
                case kParamPartPitchBendBase: c.bend = v; engine.setPartPitchBend(p, v); break;
                case kParamPartArticulationBase: c.art = v; engine.setPartArticulation(p, artFromNormalized(v)); break;
                case kParamPartTransitionSpeedBase: c.transition = v; engine.setPartTransitionSpeed(p, v); break;
                case kParamPartShortTightnessBase: c.tightness = v; engine.setPartShortTightness(p, v); break;
                case kParamPartAttackCharacterBase: c.attack = v; engine.setPartAttackCharacter(p, v); break;
                case kParamPartSpeedProfileBase: c.speedProfile = v; engine.setPartSpeedProfile(p, v); break;
                default: break;
            }
            shadow.pushControl(projectStart + offset, p, static_cast<float>(hostTempoBpm), toShadow(c));
            return;
        }
        if(id>=kParamStageFeedGainBase && id<kParamStageFeedGainBase+16){
            stageFeedGain[static_cast<std::size_t>(id-kParamStageFeedGainBase)]=v;
            return;
        }
        switch (id) {
            case kParamMode: mode = v; runtimeState(offset); break;
            case kParamActivePart: activePart = v; break;
            case kParamHumanize: humanize = v; engine.setHumanize(v); break;
            case kParamAIMix: aiMix = v; runtimeState(offset); break;
            case kParamLayoutMode: layoutMode = v; break;
            case kParamSingleInstrument: singleInstrument = v; break;
            case kParamAIAssist: aiAssist = v; runtimeState(offset); break;
            case kParamLookAhead: lookAhead = v; runtimeState(offset); break;
            case kParamAutoDivisi: autoDivisi = v; break;
            case kParamPerformanceStyle: performanceStyle=v; runtimeState(offset); break;
            case kParamSmartDynamics: smartDynamics=v; runtimeState(offset); break;
            case kParamSmartArticulation: smartArticulation=v; runtimeState(offset); break;
            case kParamRetakeTarget: retakeTarget=v; runtimeState(offset); break;
            case kParamRetakeAmount: retakeAmount=v; runtimeState(offset); break;
            case kParamRetakeNonce: retakeNonce=v; runtimeState(offset); break;
            case kParamStagePerspective: stagePerspective=v; runtimeState(offset); break;
            case kParamPolyphony: polyphony=v; runtimeState(offset); break;
            case kParamMidiAuthorityLock: midiAuthorityLock=v; runtimeState(offset); break;
            case kParamPhraseDirector: phraseDirector=v; runtimeState(offset); break;
            case kParamEnsembleLooseness: ensembleLooseness=v; runtimeState(offset); break;
            case kParamStageMixerEnable: stageMixerEnable=v; break;
            case kParamStageMasterGain: stageMasterGain=v; break;
            case kParamStageOutputGain: stageOutputGain=v; break;
            case kParamHostScopeMode: hostScopeMode=v; runtimeState(offset); break;
            case kParamHostScopeStyle: hostScopeStyle=v; runtimeState(offset); break;
            case kParamHostScopeLooseness: hostScopeLooseness=v; runtimeState(offset); break;
            case kParamTakeCarouselMode: takeCarouselMode=v; runtimeState(offset); break;
            case kParamTakeCarouselSelect: takeCarouselSelect=v; runtimeState(offset); break;
            case kParamTakeCarouselFreeze: takeCarouselFreeze=v; runtimeState(offset); break;
            case kParamTakeCompMode: takeCompMode=v; runtimeState(offset); break;
            case kParamTakeCompPhraseLength: takeCompPhraseLength=v; runtimeState(offset); break;
            case kParamTakeCompCommit: {
                const bool high=v>=.5f;
                if(high != takeCompCommitLatch && hostWindow.valid && blockQuarterValid) {
                    const double q=quarterAtOffset(offset);
                    const double len=1.0 + std::clamp(static_cast<double>(takeCompPhraseLength),0.0,1.0)*15.0;
                    const int take = (std::clamp(static_cast<int>(takeCarouselMode*2.f+.5f),0,2)==kTakeCarouselManual)
                                   ? takeIndexFromNormalized(takeCarouselSelect) : takeCarouselTracker.activeTake();
                    const auto key=phraseKeyFromQuarterV34(q,len);phraseTakeComp.commit(key,take);const auto saved=memoryCursorKey;memoryCursorKey=key;learnPreference(3,take);memoryCursorKey=saved;
                }
                takeCompCommitLatch=high; takeCompCommit=v; runtimeState(offset); break;
            }
            case kParamTakeCompClear: {
                const bool high=v>=.5f;
                if(high != takeCompClearLatch) phraseTakeComp.clear();
                takeCompClearLatch=high; takeCompClear=v; runtimeState(offset); break;
            }
            case kParamTakeCompUndo: {
                const bool high=v>=.5f;
                if(high != takeCompUndoLatch) phraseTakeComp.undo();
                takeCompUndoLatch=high; takeCompUndo=v; runtimeState(offset); break;
            }
            case kParamTakeCompRedo: {
                const bool high=v>=.5f;
                if(high != takeCompRedoLatch) phraseTakeComp.redo();
                takeCompRedoLatch=high; takeCompRedo=v; runtimeState(offset); break;
            }
            case kParamTakeCompFavorite:
            case kParamTakeCompReject: {
                const bool high=v>=.5f;
                bool& latch = (id==kParamTakeCompFavorite) ? takeCompFavoriteLatch : takeCompRejectLatch;
                if(high != latch && hostWindow.valid && blockQuarterValid) {
                    const double q=quarterAtOffset(offset);
                    const double len=1.0 + std::clamp(static_cast<double>(takeCompPhraseLength),0.0,1.0)*15.0;
                    const int take = (std::clamp(static_cast<int>(takeCarouselMode*2.f+.5f),0,2)==kTakeCarouselManual)
                                   ? takeIndexFromNormalized(takeCarouselSelect) : takeCarouselTracker.activeTake();
                    const auto key=phraseKeyFromQuarterV34(q,len);if(id==kParamTakeCompFavorite) phraseTakeComp.toggleFavorite(key,take);else phraseTakeComp.toggleReject(key,take);PersistentTakeCompEntry pq{};if(phraseTakeComp.query(key,pq)){const auto saved=memoryCursorKey;memoryCursorKey=key;if(id==kParamTakeCompFavorite && (pq.favoriteMask&(1u<<take)))learnPreference(1,take);if(id==kParamTakeCompReject && (pq.rejectMask&(1u<<take)))learnPreference(2,take);memoryCursorKey=saved;}
                }
                latch=high;
                if(id==kParamTakeCompFavorite) takeCompFavorite=v; else takeCompReject=v;
                runtimeState(offset); break;
            }
            case kParamTakeCompCommitAll: {
                const bool high=v>=.5f;
                if(high != takeCompCommitAllLatch && hostWindow.valid) {
                    const double len=1.0 + std::clamp(static_cast<double>(takeCompPhraseLength),0.0,1.0)*15.0;
                    const auto first=phraseKeyFromQuarterV34(hostWindow.startQuarter,len);
                    const auto last=phraseKeyStrictlyBeforeQuarterV35(hostWindow.endQuarter,len);
                    const int take = (std::clamp(static_cast<int>(takeCarouselMode*2.f+.5f),0,2)==kTakeCarouselManual)
                                   ? takeIndexFromNormalized(takeCarouselSelect) : takeCarouselTracker.activeTake();
                    phraseTakeComp.commitRange(first,last,take);
                }
                takeCompCommitAllLatch=high; takeCompCommitAll=v; runtimeState(offset); break;
            }
            case kParamMemoryFollowPlayhead:
                memoryFollowPlayhead=v; syncMemoryCursor(offset); break;
            case kParamMemoryRecallTake:
                memoryRecallTake=v; break;
            case kParamMemoryPrev:
            case kParamMemoryNext:
            case kParamMemoryNextUnresolved: {
                const bool high=v>=.5f;
                bool* latch = id==kParamMemoryPrev ? &memoryPrevLatch :
                              (id==kParamMemoryNext ? &memoryNextLatch : &memoryNextUnresolvedLatch);
                if(high != *latch) {
                    const auto w=memoryWindow();
                    if(memoryFollowPlayhead>=.5f) {
                        syncMemoryCursor(offset);
                        memoryFollowPlayhead=0.f;
                        emitOutputParam(kParamMemoryFollowPlayhead,0.f);
                    }
                    if(id==kParamMemoryPrev) memoryCursorKey=nextMemoryPhrase(memoryCursorKey,w,-1);
                    else if(id==kParamMemoryNext) memoryCursorKey=nextMemoryPhrase(memoryCursorKey,w,1);
                    else memoryCursorKey=nextUnresolvedPhrase(phraseTakeComp,memoryCursorKey,w);
                }
                *latch=high;
                if(id==kParamMemoryPrev) memoryPrev=v;
                else if(id==kParamMemoryNext) memoryNext=v;
                else memoryNextUnresolved=v;
                break;
            }
            case kParamMemoryRecallApply: {
                const bool high=v>=.5f;
                if(high != memoryRecallApplyLatch) {
                    const int take=takeIndexFromNormalized(memoryRecallTake);
                    takeCarouselMode=.5f; // StringList: Off=0, Manual=.5, Auto Loop=1
                    takeCarouselSelect=static_cast<float>(take)/3.f;
                    takeCarouselTracker.reset(take);
                    emitOutputParam(kParamTakeCarouselMode,takeCarouselMode);
                    emitOutputParam(kParamTakeCarouselSelect,takeCarouselSelect);
                    runtimeState(offset);
                }
                memoryRecallApplyLatch=high; memoryRecallApply=v; break;
            }
            case kParamMemoryCommitRecall:
            case kParamMemoryFavoriteRecall:
            case kParamMemoryRejectRecall:
            case kParamMemoryClearPhrase: {
                const bool high=v>=.5f;
                bool* latch = id==kParamMemoryCommitRecall ? &memoryCommitRecallLatch :
                              (id==kParamMemoryFavoriteRecall ? &memoryFavoriteRecallLatch :
                              (id==kParamMemoryRejectRecall ? &memoryRejectRecallLatch : &memoryClearPhraseLatch));
                if(high != *latch) {
                    syncMemoryCursor(offset);
                    const int take=takeIndexFromNormalized(memoryRecallTake);
                    if(id==kParamMemoryCommitRecall) {phraseTakeComp.commit(memoryCursorKey,take);learnPreference(3,take);}
                    else if(id==kParamMemoryFavoriteRecall) {phraseTakeComp.toggleFavorite(memoryCursorKey,take);PersistentTakeCompEntry q{};if(phraseTakeComp.query(memoryCursorKey,q)&&(q.favoriteMask&(1u<<take)))learnPreference(1,take);}
                    else if(id==kParamMemoryRejectRecall) {phraseTakeComp.toggleReject(memoryCursorKey,take);PersistentTakeCompEntry q{};if(phraseTakeComp.query(memoryCursorKey,q)&&(q.rejectMask&(1u<<take)))learnPreference(2,take);}
                    else phraseTakeComp.erase(memoryCursorKey);
                    runtimeState(offset);
                }
                *latch=high;
                if(id==kParamMemoryCommitRecall) memoryCommitRecall=v;
                else if(id==kParamMemoryFavoriteRecall) memoryFavoriteRecall=v;
                else if(id==kParamMemoryRejectRecall) memoryRejectRecall=v;
                else memoryClearPhrase=v;
                break;
            }
            case kParamSmartRankMode:
                smartRankMode=v; break;
            case kParamSmartAudition:
            case kParamSmartCommit: {
                const bool high=v>=.5f;
                bool& latch=(id==kParamSmartAudition)?smartAuditionLatch:smartCommitLatch;
                if(high != latch) {
                    syncMemoryCursor(offset);
                    const int rankMode=std::clamp(static_cast<int>(smartRankMode*2.f+.5f),0,2);
                    const int target=std::clamp(static_cast<int>(retakeTarget*7.f+.5f),0,7);
                    const auto ranked=smartRankTakeV36(phraseTakeComp,memoryCursorKey,retakeNonce,target,
                                                       retakeAmount,midiAuthorityLock>=.5f,rankMode);
                    const auto judgeRange=memoryPhraseSampleRange();
                    const auto judgeSnap=shadow.takeJudgeSnapshot();
                    PersistentTakeCompEntry judgeEntry{};uint8_t judgeFav=0,judgeRej=0;
                    if(phraseTakeComp.query(memoryCursorKey,judgeEntry)){judgeFav=judgeEntry.favoriteMask;judgeRej=judgeEntry.rejectMask;}
                    const bool judgeUsable=judgeRange[1]>judgeRange[0] && judgeSnap.generation>0 &&
                                           judgeSnap.startSample==judgeRange[0] && judgeSnap.configToken==judgeConfigToken(judgeFav,judgeRej,judgeScopedState(),judgePhraseTempo()) &&
                                           judgeSnap.winner>=0 && judgeSnap.winner<4 && (judgeSnap.validMask&(1u<<judgeSnap.winner)) && judgeMatchesCurrentProfile(judgeSnap);
                    const int selectedTake=judgeUsable?judgeSnap.winner:ranked.take;
                    if(selectedTake>=0) {
                        if(id==kParamSmartAudition) {
                            memoryRecallTake=static_cast<float>(selectedTake)/3.f;
                            takeCarouselMode=.5f;
                            takeCarouselSelect=memoryRecallTake;
                            takeCarouselTracker.reset(selectedTake);
                            emitOutputParam(kParamMemoryRecallTake,memoryRecallTake);
                            emitOutputParam(kParamTakeCarouselMode,takeCarouselMode);
                            emitOutputParam(kParamTakeCarouselSelect,takeCarouselSelect);
                        } else {
                            phraseTakeComp.commit(memoryCursorKey,selectedTake); learnPreference(3,selectedTake);
                        }
                        runtimeState(offset);
                    }
                }
                latch=high;
                if(id==kParamSmartAudition) smartAudition=v; else smartCommit=v;
                break;
            }
            case kParamCommitUniqueFavorites:
            case kParamAutoCompUnresolved: {
                const bool high=v>=.5f;
                bool& latch=(id==kParamCommitUniqueFavorites)?commitUniqueFavoritesLatch:autoCompUnresolvedLatch;
                if(high != latch) {
                    const auto w=memoryWindow();
                    if(w.valid) {
                        std::array<std::int64_t,PersistentPhraseTakeComp::kCapacity> keys{};
                        std::array<std::uint8_t,PersistentPhraseTakeComp::kCapacity> takes{};
                        int count=0;
                        const int rankMode=std::clamp(static_cast<int>(smartRankMode*2.f+.5f),0,2);
                        const int target=std::clamp(static_cast<int>(retakeTarget*7.f+.5f),0,7);
                        const std::int64_t total=std::min<std::int64_t>(PersistentPhraseTakeComp::kCapacity,w.lastKey-w.firstKey+1);
                        for(std::int64_t i=0;i<total && count<PersistentPhraseTakeComp::kCapacity;++i) {
                            const auto key=w.firstKey+i;
                            int committedTake=-1;
                            if(phraseTakeComp.lookup(key,committedTake)) continue;
                            int take=-1;
                            if(id==kParamCommitUniqueFavorites) take=uniqueFavoriteTakeV36(phraseTakeComp,key);
                            else take=smartRankTakeV36(phraseTakeComp,key,retakeNonce,target,retakeAmount,
                                                       midiAuthorityLock>=.5f,rankMode).take;
                            if(take<0) continue;
                            keys[static_cast<std::size_t>(count)]=key;
                            takes[static_cast<std::size_t>(count)]=static_cast<std::uint8_t>(take);
                            ++count;
                        }
                        if(count>0) phraseTakeComp.commitBatch(keys,takes,count);
                        runtimeState(offset);
                    }
                }
                latch=high;
                if(id==kParamCommitUniqueFavorites) commitUniqueFavorites=v; else autoCompUnresolved=v;
                break;
            }
            case kParamJudgeTrigger: {
                const bool high=v>=.5f;
                if(high != judgeTriggerLatch) {
                    syncMemoryCursor(offset);
                    const auto range=memoryPhraseSampleRange();
                    PersistentTakeCompEntry entry{};
                    uint8_t fav=0,rej=0;
                    if(phraseTakeComp.query(memoryCursorKey,entry)){fav=entry.favoriteMask;rej=entry.rejectMask;}
                    const auto scoped=judgeScopedState();const float phraseTempo=judgePhraseTempo();
                    const uint64_t token=judgeConfigToken(fav,rej,scoped,phraseTempo);
                    if(range[1]>range[0]) shadow.requestTakeJudge(range[0],range[1],scoped.retakeNonce,fav,rej,token,judgePolicyFlags(scoped),
                                                                  std::max(1,std::clamp(int(mode*2.f+.5f),0,2)),phraseTempo,lookAhead,personalTasteEnable>=.5f,personalTasteStrength);
                }
                judgeTriggerLatch=high;judgeTrigger=v;break;
            }
            case kParamJudgeAuditionWinner:
            case kParamJudgeCommitWinner: {
                const bool high=v>=.5f;
                bool& latch=id==kParamJudgeAuditionWinner?judgeAuditionWinnerLatch:judgeCommitWinnerLatch;
                if(high != latch) {
                    syncMemoryCursor(offset);
                    const auto range=memoryPhraseSampleRange();
                    const auto snap=shadow.takeJudgeSnapshot();
                    PersistentTakeCompEntry judgeEntry{};uint8_t judgeFav=0,judgeRej=0;
                    if(phraseTakeComp.query(memoryCursorKey,judgeEntry)){judgeFav=judgeEntry.favoriteMask;judgeRej=judgeEntry.rejectMask;}
                    if(range[1]>range[0] && snap.startSample==range[0] && snap.configToken==judgeConfigToken(judgeFav,judgeRej,judgeScopedState(),judgePhraseTempo()) && snap.winner>=0 && snap.winner<4 &&
                       (snap.validMask&(1u<<snap.winner)) && judgeMatchesCurrentProfile(snap)) {
                        if(id==kParamJudgeAuditionWinner) {
                            memoryRecallTake=static_cast<float>(snap.winner)/3.f;
                            takeCarouselMode=.5f;takeCarouselSelect=memoryRecallTake;takeCarouselTracker.reset(snap.winner);
                            emitOutputParam(kParamMemoryRecallTake,memoryRecallTake);
                            emitOutputParam(kParamTakeCarouselMode,takeCarouselMode);
                            emitOutputParam(kParamTakeCarouselSelect,takeCarouselSelect);
                        } else {phraseTakeComp.commit(memoryCursorKey,snap.winner);learnPreference(3,snap.winner);}
                        runtimeState(offset);
                    }
                }
                latch=high;
                if(id==kParamJudgeAuditionWinner) judgeAuditionWinner=v; else judgeCommitWinner=v;
                break;
            }
            case kParamPersonalTasteEnable: personalTasteEnable=v; break;
            case kParamPersonalTasteStrength: personalTasteStrength=v; break;
            case kParamPersonalTasteLearn: personalTasteLearn=v; break;
            case kParamPersonalTasteClear: {const bool high=v>=.5f;if(high!=personalTasteClearLatch)preference.clear();personalTasteClearLatch=high;personalTasteClear=v;break;}
            case kParamPreferenceMinConfidence: preferenceMinConfidence=v; break;
            case kParamPreferenceMinMargin: preferenceMinMargin=v; break;
            case kParamPreferenceSafetyFloor: preferenceSafetyFloor=v; break;
            case kParamPreferenceAutoCompCancel: {const bool high=v>=.5f;if(high!=preferenceAutoCompCancelLatch){preferenceAutoCompRunning=false;preferenceAutoCompWaiting=false;preferenceCandidateCount=0;}preferenceAutoCompCancelLatch=high;preferenceAutoCompCancel=v;break;}
            case kParamPreferenceAutoComp: {const bool high=v>=.5f;if(high!=preferenceAutoCompLatch && hostWindow.valid){const auto w=memoryWindow();preferenceJobCount=preferenceJobIndex=preferenceCandidateCount=preferenceReviewCount=0;preferenceAutoCompWaiting=false;++preferenceBatchId;if(w.valid){const auto total=std::min<std::int64_t>(PersistentPhraseTakeComp::kCapacity,w.lastKey-w.firstKey+1);for(std::int64_t i=0;i<total;++i){const auto key=w.firstKey+i;int tk=-1;if(!phraseTakeComp.lookup(key,tk))preferenceJobKeys[preferenceJobCount++]=key;}}preferenceAutoCompRunning=preferenceJobCount>0;}preferenceAutoCompLatch=high;preferenceAutoComp=v;break;}
            default: break;
        }
    };

    // Collect all automation points into a fixed-size scratch buffer: no heap allocation in process().
    // Applying exact VST3 sample offsets is especially important for CC1/CC3/CC11/CC20 musical curves.
    std::array<AutomationPoint, kMaxAutomationPointsPerBlock> automation {};
    std::size_t automationCount = 0;
    if (data.inputParameterChanges) {
        const int32 queues = data.inputParameterChanges->getParameterCount();
        for (int32 qi = 0; qi < queues; ++qi) {
            auto* q = data.inputParameterChanges->getParameterData(qi);
            if (!q) continue;
            const auto id = q->getParameterId();
            const int32 points = q->getPointCount();
            for (int32 pi = 0; pi < points && automationCount < automation.size(); ++pi) {
                int32 off = 0; ParamValue pv = 0.0;
                if (q->getPoint(pi, off, pv) == kResultTrue) {
                    automation[automationCount++] = {
                        std::clamp(off, 0, data.numSamples), id, static_cast<float>(pv)
                    };
                }
            }
        }
    }
    std::sort(automation.begin(), automation.begin() + static_cast<std::ptrdiff_t>(automationCount),
              [](const AutomationPoint& a, const AutomationPoint& b) {
                  if (a.sampleOffset != b.sampleOffset) return a.sampleOffset < b.sampleOffset;
                  return a.id < b.id;
              });

    // Periodic state snapshot covers long steady passages without automation events.
    const int64_t every = std::max<int64_t>(1, static_cast<int64_t>((data.processContext ? data.processContext->sampleRate : 48000.0) * .10));
    if (projectStart - lastControlPush >= every || projectStart < lastControlPush) {
        for (int p = 0; p < kPartCount; ++p)
            shadow.pushControl(projectStart, p, static_cast<float>(hostTempoBpm), toShadow(part[p]));
        lastControlPush = projectStart;
    }

    if (data.numOutputs < 1 || data.outputs[0].numChannels < 2 || data.symbolicSampleSize != kSample32)
        return kResultOk;

    auto** out = data.outputs[0].channelBuffers32;
    std::array<float*, kAuxFeedCount> auxL{};
    std::array<float*, kAuxFeedCount> auxR{};
    int auxPairs = 0;
    for (int32 bus = 0; bus < data.numOutputs; ++bus) {
        auto& b = data.outputs[bus];
        if (b.numChannels < 2 || !b.channelBuffers32) continue;
        std::memset(b.channelBuffers32[0], 0, sizeof(float) * data.numSamples);
        std::memset(b.channelBuffers32[1], 0, sizeof(float) * data.numSamples);
        if (bus > 0 && auxPairs < kAuxFeedCount) { auxL[auxPairs] = b.channelBuffers32[0]; auxR[auxPairs] = b.channelBuffers32[1]; ++auxPairs; }
    }

    Event nextEvent {};
    int32 eventIndex = 0;
    const int32 eventCount = data.inputEvents ? data.inputEvents->getEventCount() : 0;
    bool haveEvent = eventCount > 0 && data.inputEvents->getEvent(0, nextEvent) == kResultOk;
    std::size_t autoIndex = 0;
    std::size_t scopeBoundaryIndex = 0;
    int32 cursor = 0;

    auto handleEvent = [&](const Event& e, int32 pos) noexcept {
        if (e.type == Event::kNoteOnEvent) {
            const int rawCh = e.noteOn.channel;
            if(rawCh<0||rawCh>=16)return;
            const int selected = std::clamp(static_cast<int>(singleInstrument * 3.f + .5f), 0, 3);
            const int note = e.noteOn.pitch;
            const bool laneExplicit=(rawCh>=4)||(voiceLane[rawCh].mask!=0);
            const bool divisi = layoutMode >= .5f && autoDivisi >= .5f && rawCh == 0 && !laneExplicit && !isKeyswitch(note);
            int ch = (layoutMode < .5f) ? selected : stringPartForMidiChannel(rawCh);
            if (isKeyswitch(note) && layoutMode >= .5f && autoDivisi >= .5f && rawCh == 0 && !laneExplicit) {
                const int a = articulationFromKeyswitch(note);
                for (int p=0;p<kPartCount;++p) {
                    part[p].art = static_cast<float>(a) / static_cast<float>(kArticulationCount - 1);
                    engine.setPartArticulation(p, a);
                    shadow.pushMidi(ShadowRenderClient::Keyswitch, projectStart + pos, p, note, a, 0.f,
                                    static_cast<float>(hostTempoBpm), toShadow(part[p]));
                }
                return;
            }
            if (divisi) {
                ch = chooseDivisiPart(note);
                divisiOwner[rawCh][note] = static_cast<int8_t>(ch + 1);
                ++divisiActive[ch];
            }
            if (ch < 0 || ch >= kPartCount) return;

            if (isKeyswitch(note)) {
                const int a = articulationFromKeyswitch(note);
                if(laneExplicit){
                    auto& o=voiceLane[rawCh];o.art=static_cast<float>(a)/static_cast<float>(kArticulationCount-1);o.mask|=0x40;
                    const auto c=mergedVoiceControl(rawCh);
                    engine.updateVoiceLaneControl(rawCh,previewVoiceControl(rawCh,c));
                    const int packed=packArticulationExpression(a,expressionStackFromNormalized(c.stack));
                    shadow.pushMidi(ShadowRenderClient::Keyswitch,projectStart+pos,encodeShadowStringPart(ch,rawCh),note,packed,0.f,
                                    static_cast<float>(hostTempoBpm),toShadow(c));
                }else{
                    part[ch].art = static_cast<float>(a) / static_cast<float>(kArticulationCount - 1);
                    engine.setPartArticulation(ch, a);
                    shadow.pushMidi(ShadowRenderClient::Keyswitch, projectStart + pos, ch, note, a, 0.f,
                                    static_cast<float>(hostTempoBpm), toShadow(part[ch]));
                }
            } else if(laneExplicit) {
                const auto c=mergedVoiceControl(rawCh);
                const int baseArt=artFromNormalized(c.art);
                const auto stack=expressionStackFromNormalized(c.stack);
                engine.noteOnVoice(ch,rawCh,note,e.noteOn.velocity,previewVoiceControl(rawCh,c));
                shadow.pushMidi(ShadowRenderClient::NoteOn,projectStart+pos,encodeShadowStringPart(ch,rawCh),note,
                                packArticulationExpression(baseArt,stack),e.noteOn.velocity,
                                static_cast<float>(hostTempoBpm),toShadow(c));
            } else {
                engine.noteOn(ch, note, e.noteOn.velocity);
                shadow.pushMidi(ShadowRenderClient::NoteOn, projectStart + pos, ch, note,
                                artFromNormalized(part[ch].art), e.noteOn.velocity,
                                static_cast<float>(hostTempoBpm), toShadow(part[ch]));
            }
        } else if (e.type == Event::kNoteOffEvent) {
            const int rawCh = e.noteOff.channel;
            if(rawCh<0||rawCh>=16)return;
            const int selected = std::clamp(static_cast<int>(singleInstrument * 3.f + .5f), 0, 3);
            const int note = e.noteOff.pitch;
            const bool laneExplicit=(rawCh>=4)||(voiceLane[rawCh].mask!=0);
            int ch = (layoutMode < .5f) ? selected : stringPartForMidiChannel(rawCh);
            if (layoutMode >= .5f && autoDivisi >= .5f && rawCh == 0 && !laneExplicit && note>=0 && note<128) {
                const int owner = divisiOwner[rawCh][note];
                if (owner > 0) { ch = owner - 1; divisiOwner[rawCh][note] = 0; divisiActive[ch] = std::max(0, divisiActive[ch]-1); }
            }
            if (ch < 0 || ch >= kPartCount || isKeyswitch(note)) return;
            if(laneExplicit){
                const auto c=mergedVoiceControl(rawCh);
                engine.noteOffVoice(ch,rawCh,note);
                shadow.pushMidi(ShadowRenderClient::NoteOff,projectStart+pos,encodeShadowStringPart(ch,rawCh),note,
                                packArticulationExpression(artFromNormalized(c.art),expressionStackFromNormalized(c.stack)),0.f,
                                static_cast<float>(hostTempoBpm),toShadow(c));
            }else{
                engine.noteOff(ch, note);
                shadow.pushMidi(ShadowRenderClient::NoteOff, projectStart + pos, ch, note,
                                artFromNormalized(part[ch].art), 0.f,
                                static_cast<float>(hostTempoBpm), toShadow(part[ch]));
            }
        }
    };

    // Merge VST3 parameter and MIDI timelines. Parameter points at a sample are applied before
    // note events at that same sample so a note onset sees the intended CC state.
    while (cursor < data.numSamples || autoIndex < automationCount || haveEvent || scopeBoundaryIndex < scopeBoundaryCount) {
        const int32 nextAuto = autoIndex < automationCount ? automation[autoIndex].sampleOffset : data.numSamples;
        const int32 nextMidi = haveEvent ? std::clamp(nextEvent.sampleOffset, 0, data.numSamples) : data.numSamples;
        const int32 nextScope = scopeBoundaryIndex < scopeBoundaryCount ? scopeBoundaries[scopeBoundaryIndex] : data.numSamples;
        const int32 nextPos = std::min({nextAuto, nextMidi, nextScope});

        if (nextPos > cursor) {
            engine.render(out[0] + cursor, out[1] + cursor, nextPos - cursor);
            cursor = nextPos;
        }

        while (scopeBoundaryIndex < scopeBoundaryCount && scopeBoundaries[scopeBoundaryIndex] == nextPos) {
            runtimeState(nextPos);
            ++scopeBoundaryIndex;
        }

        while (autoIndex < automationCount && automation[autoIndex].sampleOffset == nextPos) {
            applyParameter(automation[autoIndex].id, automation[autoIndex].value, nextPos);
            ++autoIndex;
        }

        while (haveEvent && std::clamp(nextEvent.sampleOffset, 0, data.numSamples) == nextPos) {
            handleEvent(nextEvent, nextPos);
            ++eventIndex;
            if (eventIndex < eventCount && data.inputEvents->getEvent(eventIndex, nextEvent) == kResultOk)
                haveEvent = true;
            else
                haveEvent = false;
        }

        if (nextPos >= data.numSamples) break;
        // Guard malformed event/automation input from stalling the audio thread.
        if (nextPos == cursor && nextAuto > cursor && nextMidi > cursor && nextScope > cursor) break;
    }

    if (cursor < data.numSamples)
        engine.render(out[0] + cursor, out[1] + cursor, data.numSamples - cursor);

    // v3.9: one async Audio Judge at a time; candidates commit once at batch end (one Undo snapshot).
    if(preferenceAutoCompRunning){
        if(preferenceAutoCompWaiting){
            const auto snap=shadow.takeJudgeSnapshot();
            if(snap.generation>preferenceJudgeGeneration && snap.startSample==preferencePendingStart && snap.configToken==preferencePendingToken){
                const auto profile=personalProfile(); const bool profileMatch=personalTasteEnable<.5f || (snap.profileHash32!=0 && snap.profileHash32==uint32_t(profile.hash&0xFFFFFFFFu));
                const auto gate=evaluatePreferenceAutoCompV39(profileMatch&&personalTasteEnable>=.5f,profile.confidence,preferenceMinConfidence,preferenceMinMargin,preferenceSafetyFloor,snap.validMask,snap.personal,snap.safety);
                if(gate.commit && preferenceCandidateCount<PersistentPhraseTakeComp::kCapacity){preferenceCandidateKeys[preferenceCandidateCount]=preferencePendingKey;preferenceCandidateTakes[preferenceCandidateCount]=uint8_t(gate.take);++preferenceCandidateCount;}else ++preferenceReviewCount;
                ++preferenceJobIndex;preferenceAutoCompWaiting=false;
            }
        } else if(preferenceJobIndex<preferenceJobCount){
            const auto saved=memoryCursorKey;memoryCursorKey=preferenceJobKeys[preferenceJobIndex];const auto range=memoryPhraseSampleRange();PersistentTakeCompEntry e{};uint8_t fav=0,rej=0;if(phraseTakeComp.query(memoryCursorKey,e)){fav=e.favoriteMask;rej=e.rejectMask;}const auto scoped=judgeScopedState();const float phraseTempo=judgePhraseTempo();const auto token=judgeConfigToken(fav,rej,scoped,phraseTempo);const auto before=shadow.takeJudgeSnapshot();
            if(range[1]>range[0]){shadow.requestTakeJudge(range[0],range[1],scoped.retakeNonce,fav,rej,token,judgePolicyFlags(scoped),std::max(1,std::clamp(int(mode*2.f+.5f),0,2)),phraseTempo,lookAhead,true,personalTasteStrength);preferencePendingKey=memoryCursorKey;preferencePendingStart=range[0];preferencePendingToken=token;preferenceJudgeGeneration=before.generation;preferenceAutoCompWaiting=true;}else{++preferenceReviewCount;++preferenceJobIndex;}memoryCursorKey=saved;
        } else {
            if(preferenceCandidateCount>0)phraseTakeComp.commitBatch(preferenceCandidateKeys,preferenceCandidateTakes,preferenceCandidateCount);preferenceAutoCompRunning=false;preferenceAutoCompWaiting=false;
        }
    }

    shadow.mix(out[0], out[1], auxL.data(), auxR.data(), auxPairs, data.numSamples, projectStart);

    // v6.4 microphone mixer. The legacy/model master remains the default path. When enabled,
    // the master bus is reconstructed from the available geometry feeds using equal-power
    // normalization; each exposed aux feed also receives its own fader gain. No allocation/locks.
    if(stageMixerEnable>=.5f && auxPairs>0){
        double energy=0.0;
        for(int a=0;a<auxPairs;++a){const float g=std::clamp(stageFeedGain[static_cast<std::size_t>(a)],0.f,1.f);energy+=double(g)*double(g);}
        const float norm=energy>1.0 ? float(1.0/std::sqrt(energy)) : 1.f;
        const float master=std::clamp(stageMasterGain,0.f,1.f)*std::clamp(stageOutputGain,0.f,1.f);
        for(int32_t i=0;i<data.numSamples;++i){
            float ml=0.f,mr=0.f;
            for(int a=0;a<auxPairs;++a){
                const float g=std::clamp(stageFeedGain[static_cast<std::size_t>(a)],0.f,1.f);
                if(auxL[a]&&auxR[a]){ml+=auxL[a][i]*g;mr+=auxR[a][i]*g;auxL[a][i]*=g;auxR[a][i]*=g;}
            }
            out[0][i]=ml*norm*master;out[1][i]=mr*norm*master;
        }
    }else if(stageOutputGain<.9999f){
        const float g=std::clamp(stageOutputGain,0.f,1.f);
        for(int32_t i=0;i<data.numSamples;++i){out[0][i]*=g;out[1][i]*=g;}
    }

    // v3.5 processor-owned memory status is reported back through VST3 output parameter changes.
    // It is read-only from the controller's perspective and never consumes MIDI CCs.
    syncMemoryCursor(data.numSamples > 0 ? data.numSamples-1 : 0);
    const int recallTake=takeIndexFromNormalized(memoryRecallTake);
    const auto memStatus=performanceMemoryStatus(phraseTakeComp,memoryCursorKey,recallTake,memoryWindow());
    emitOutputParam(kParamMemoryCommittedTake, memStatus.committed ? static_cast<float>(memStatus.committedTake+1)/4.f : 0.f);
    emitOutputParam(kParamMemoryRecallFavorite, memStatus.recallFavorite ? 1.f : 0.f);
    emitOutputParam(kParamMemoryRecallRejected, memStatus.recallRejected ? 1.f : 0.f);
    emitOutputParam(kParamMemoryCoverage, memStatus.coverage);
    emitOutputParam(kParamMemoryCursorPosition, memStatus.cursorPosition);

    const int rankMode=std::clamp(static_cast<int>(smartRankMode*2.f+.5f),0,2);
    const int target=std::clamp(static_cast<int>(retakeTarget*7.f+.5f),0,7);
    const auto timeline=smartTimelineWindowV36(memoryCursorKey,memoryWindow());
    int unresolvedSlots=0;
    for(int slot=0;slot<8;++slot) {
        float committedNorm=0.f,smartNorm=0.f;
        if(slot<timeline.count) {
            const auto key=timeline.phraseKeys[static_cast<std::size_t>(slot)];
            PersistentTakeCompEntry e{};
            if(phraseTakeComp.query(key,e) && e.committed) committedNorm=static_cast<float>(e.takeIndex+1)/4.f;
            else ++unresolvedSlots;
            const auto ranked=smartRankTakeV36(phraseTakeComp,key,retakeNonce,target,retakeAmount,
                                               midiAuthorityLock>=.5f,rankMode);
            int smartTake=ranked.take;
            if(key==memoryCursorKey) {
                const auto jr=memoryPhraseSampleRange();
                const auto js=shadow.takeJudgeSnapshot();
                PersistentTakeCompEntry judgeEntry{};uint8_t judgeFav=0,judgeRej=0;
                if(phraseTakeComp.query(memoryCursorKey,judgeEntry)){judgeFav=judgeEntry.favoriteMask;judgeRej=judgeEntry.rejectMask;}
                if(jr[1]>jr[0] && js.generation>0 && js.startSample==jr[0] && js.configToken==judgeConfigToken(judgeFav,judgeRej,judgeScopedState(),judgePhraseTempo()) && js.winner>=0 && js.winner<4 &&
                   (js.validMask&(1u<<js.winner)) && judgeMatchesCurrentProfile(js)) smartTake=js.winner;
            }
            if(smartTake>=0) smartNorm=static_cast<float>(smartTake+1)/4.f;
        }
        emitOutputParam(timelineParam(kParamTimelineCommittedBase,slot),committedNorm);
        emitOutputParam(timelineParam(kParamTimelineSmartPickBase,slot),smartNorm);
    }
    const auto currentRank=smartRankTakeV36(phraseTakeComp,memoryCursorKey,retakeNonce,target,retakeAmount,
                                            midiAuthorityLock>=.5f,rankMode);
    emitOutputParam(kParamSmartScore,currentRank.score);
    emitOutputParam(kParamSmartVariation,currentRank.variation);
    emitOutputParam(kParamTimelineCursorSlot,
                    static_cast<float>(std::clamp(timeline.cursorSlot,0,7))/7.f);
    emitOutputParam(kParamTimelineUnresolved,timeline.count>0 ?
                    static_cast<float>(unresolvedSlots)/static_cast<float>(timeline.count) : 0.f);

    const auto judgeRange=memoryPhraseSampleRange();
    const auto judge=shadow.takeJudgeSnapshot();
    PersistentTakeCompEntry judgeEntry{};uint8_t judgeFav=0,judgeRej=0;
    if(phraseTakeComp.query(memoryCursorKey,judgeEntry)){judgeFav=judgeEntry.favoriteMask;judgeRej=judgeEntry.rejectMask;}
    const bool judgeMatches=judgeRange[1]>judgeRange[0] && judge.startSample==judgeRange[0] && judge.generation>0 &&
                            judge.configToken==judgeConfigToken(judgeFav,judgeRej,judgeScopedState(),judgePhraseTempo()) && judgeMatchesCurrentProfile(judge);
    emitOutputParam(kParamJudgeWinner,judgeMatches && judge.winner>=0 ? static_cast<float>(judge.winner+1)/4.f : 0.f);
    for(int take=0;take<4;++take){
        const bool valid=judgeMatches && ((judge.validMask&(1u<<take))!=0);
        emitOutputParam(judgeParam(kParamJudgeOverallBase,take),valid?judge.overall[take]:0.f);
        emitOutputParam(judgeParam(kParamJudgeDynamicsBase,take),valid?judge.dynamics[take]:0.f);
        emitOutputParam(judgeParam(kParamJudgeAttackBase,take),valid?judge.attack[take]:0.f);
        emitOutputParam(judgeParam(kParamJudgeTransitionBase,take),valid?judge.transition[take]:0.f);
        emitOutputParam(judgeParam(kParamJudgeStabilityBase,take),valid?judge.stability[take]:0.f);
    }
    emitOutputParam(kParamJudgeWinnerSafety,judgeMatches && judge.winner>=0 && judge.winner<4 ? judge.safety[judge.winner] : 0.f);
    const auto profile=personalProfile();emitOutputParam(kParamPersonalConfidence,profile.confidence);emitOutputParam(kParamPersonalEvidence,std::clamp(profile.evidence/20.f,0.f,1.f));for(int i=0;i<5;++i)emitOutputParam(personalParam(kParamPersonalWeightBase,i),std::clamp((profile.weights[i]+1.f)*.5f,0.f,1.f));for(int i=0;i<4;++i)emitOutputParam(personalParam(kParamPersonalScoreBase,i),judgeMatches?judge.personal[i]:0.f);
    emitOutputParam(kParamPreferenceAutoCompStatus,preferenceAutoCompRunning?(preferenceAutoCompWaiting?2.f/3.f:1.f/3.f):(preferenceJobCount>0?1.f:0.f));emitOutputParam(kParamPreferenceAutoCompProgress,preferenceJobCount>0?std::clamp(float(preferenceJobIndex)/float(preferenceJobCount),0.f,1.f):0.f);emitOutputParam(kParamPreferenceAutoCompCommitted,std::clamp(float(preferenceCandidateCount)/128.f,0.f,1.f));emitOutputParam(kParamPreferenceAutoCompReview,std::clamp(float(preferenceReviewCount)/128.f,0.f,1.f));
    return kResultOk;
}

tresult PLUGIN_API Processor::setState(IBStream* state) {
    if (!state) return kResultFalse;
    IBStreamer s(state, kLittleEndian);
    int32 version = 0;
    if (!s.readInt32(version) || (version < 3 || version > kStateVersion)) return kResultFalse;
    if (!s.readFloat(mode) || !s.readFloat(activePart) || !s.readFloat(humanize) || !s.readFloat(aiMix) ||
        !s.readFloat(layoutMode) || !s.readFloat(singleInstrument) || !s.readFloat(aiAssist) ||
        !s.readFloat(lookAhead) || !s.readFloat(autoDivisi)) return kResultFalse;
    if(version>=5){if(!s.readFloat(performanceStyle)||!s.readFloat(smartDynamics)||!s.readFloat(smartArticulation)||!s.readFloat(retakeTarget)||!s.readFloat(retakeAmount)||!s.readFloat(retakeNonce)||!s.readFloat(stagePerspective)||!s.readFloat(polyphony))return kResultFalse;}
    else {performanceStyle=0.f;smartDynamics=0.f;smartArticulation=0.f;retakeTarget=0.f;retakeAmount=0.f;retakeNonce=0.f;stagePerspective=.333333f;polyphony=1.f;}
    if(version>=6){if(!s.readFloat(midiAuthorityLock)||!s.readFloat(phraseDirector)||!s.readFloat(ensembleLooseness))return kResultFalse;}
    else {midiAuthorityLock=1.f;phraseDirector=1.f;ensembleLooseness=.18f;}
    if(version>=7){if(!s.readFloat(hostScopeMode)||!s.readFloat(hostScopeStyle)||!s.readFloat(hostScopeLooseness))return kResultFalse;}
    else {hostScopeMode=0.f;hostScopeStyle=0.f;hostScopeLooseness=.30f;}
    if(version>=8){if(!s.readFloat(takeCarouselMode)||!s.readFloat(takeCarouselSelect)||!s.readFloat(takeCarouselFreeze))return kResultFalse;}
    else {takeCarouselMode=0.f;takeCarouselSelect=0.f;takeCarouselFreeze=0.f;}
    if(version>=9){if(!s.readFloat(takeCompMode)||!s.readFloat(takeCompPhraseLength))return kResultFalse;}
    else {takeCompMode=0.f;takeCompPhraseLength=.25f;}
    if(version>=11){
        int32 memoryCursor32=0;
        if(!s.readFloat(memoryFollowPlayhead)||!s.readFloat(memoryRecallTake)||!s.readInt32(memoryCursor32)) return kResultFalse;
        memoryCursorKey=static_cast<std::int64_t>(memoryCursor32);
    } else {
        memoryFollowPlayhead=1.f; memoryRecallTake=0.f; memoryCursorKey=0;
    }
    if(version>=12){ if(!s.readFloat(smartRankMode)) return kResultFalse; }
    else smartRankMode=.5f;
    if(version>=13){if(!s.readFloat(personalTasteEnable)||!s.readFloat(personalTasteStrength)||!s.readFloat(personalTasteLearn)||!s.readFloat(preferenceMinConfidence)||!s.readFloat(preferenceMinMargin)||!s.readFloat(preferenceSafetyFloor))return kResultFalse;}
    else {personalTasteEnable=1.f;personalTasteStrength=.75f;personalTasteLearn=1.f;preferenceMinConfidence=.30f;preferenceMinMargin=.10f;preferenceSafetyFloor=.35f;}
    if(version>=14){
        if(!s.readFloat(stageMixerEnable)||!s.readFloat(stageMasterGain)||!s.readFloat(stageOutputGain))return kResultFalse;
        for(float& g:stageFeedGain)if(!s.readFloat(g))return kResultFalse;
    }else{
        stageMixerEnable=0.f;stageMasterGain=1.f;stageOutputGain=1.f;
        stageFeedGain={{.25f,.35f,.25f,.45f,.62f,.45f,.28f,.28f,.20f,.20f,0.f,.12f,.12f,.06f,.06f,0.f}};
    }
    phraseTakeComp.resetAll();
    if(version>=10){
        int32 compCount=0;
        if(!s.readInt32(compCount) || compCount<0 || compCount>PersistentPhraseTakeComp::kCapacity) return kResultFalse;
        for(int32 i=0;i<compCount;++i){
            int32 phraseKey32=0,take=0,favorite=0,reject=0,committed=1;
            if(!s.readInt32(phraseKey32)||!s.readInt32(take)||!s.readInt32(favorite)||!s.readInt32(reject)) return kResultFalse;
            if(version>=11 && !s.readInt32(committed)) return kResultFalse;
            if(take<0||take>3||(favorite&~0x0F)||(reject&~0x0F)||(committed!=0&&committed!=1)) return kResultFalse;
            if(!phraseTakeComp.restoreEntry(static_cast<std::int64_t>(phraseKey32),take,favorite,reject,committed!=0)) return kResultFalse;
        }
        phraseTakeComp.finishRestore();
    }
    takeCompCommit=0.f;takeCompClear=0.f;takeCompUndo=0.f;takeCompRedo=0.f;takeCompFavorite=0.f;takeCompReject=0.f;takeCompCommitAll=0.f;
    takeCompCommitLatch=false;takeCompClearLatch=false;takeCompUndoLatch=false;takeCompRedoLatch=false;
    takeCompFavoriteLatch=false;takeCompRejectLatch=false;takeCompCommitAllLatch=false;
    memoryPrev=0.f;memoryNext=0.f;memoryNextUnresolved=0.f;memoryRecallApply=0.f;memoryCommitRecall=0.f;
    memoryFavoriteRecall=0.f;memoryRejectRecall=0.f;memoryClearPhrase=0.f;
    memoryPrevLatch=false;memoryNextLatch=false;memoryNextUnresolvedLatch=false;memoryRecallApplyLatch=false;
    memoryCommitRecallLatch=false;memoryFavoriteRecallLatch=false;memoryRejectRecallLatch=false;memoryClearPhraseLatch=false;
    smartAudition=0.f;smartCommit=0.f;commitUniqueFavorites=0.f;autoCompUnresolved=0.f;
    smartAuditionLatch=false;smartCommitLatch=false;commitUniqueFavoritesLatch=false;autoCompUnresolvedLatch=false;
    judgeTrigger=0.f;judgeAuditionWinner=0.f;judgeCommitWinner=0.f;
    judgeTriggerLatch=false;judgeAuditionWinnerLatch=false;judgeCommitWinnerLatch=false;personalTasteClear=0.f;personalTasteClearLatch=false;preferenceAutoComp=0.f;preferenceAutoCompCancel=0.f;preferenceAutoCompLatch=false;preferenceAutoCompCancelLatch=false;preferenceAutoCompRunning=false;preferenceAutoCompWaiting=false;preferenceJobCount=preferenceJobIndex=preferenceCandidateCount=preferenceReviewCount=0;
    takeCarouselTracker.reset(takeIndexFromNormalized(takeCarouselSelect));
    for (auto& c : part) {
        float* v[] = {&c.dyn,&c.vib,&c.exp,&c.vol,&c.pan,&c.sus,&c.leg,&c.room,&c.bend,&c.art,&c.transition,&c.tightness,&c.attack};
        for (float* x : v) if (!s.readFloat(*x)) return kResultFalse;
        if (version >= 4) { if (!s.readFloat(c.speedProfile)) return kResultFalse; }
        else c.speedProfile = 0.f;
    }
    return kResultOk;
}

tresult PLUGIN_API Processor::getState(IBStream* state) {
    if (!state) return kResultFalse;
    IBStreamer s(state, kLittleEndian);
    if (!s.writeInt32(kStateVersion) || !s.writeFloat(mode) || !s.writeFloat(activePart) ||
        !s.writeFloat(humanize) || !s.writeFloat(aiMix) || !s.writeFloat(layoutMode) ||
        !s.writeFloat(singleInstrument) || !s.writeFloat(aiAssist) || !s.writeFloat(lookAhead) ||
        !s.writeFloat(autoDivisi) || !s.writeFloat(performanceStyle) || !s.writeFloat(smartDynamics) || !s.writeFloat(smartArticulation) || !s.writeFloat(retakeTarget) || !s.writeFloat(retakeAmount) || !s.writeFloat(retakeNonce) || !s.writeFloat(stagePerspective) || !s.writeFloat(polyphony) || !s.writeFloat(midiAuthorityLock) || !s.writeFloat(phraseDirector) || !s.writeFloat(ensembleLooseness) || !s.writeFloat(hostScopeMode) || !s.writeFloat(hostScopeStyle) || !s.writeFloat(hostScopeLooseness) || !s.writeFloat(takeCarouselMode) || !s.writeFloat(takeCarouselSelect) || !s.writeFloat(takeCarouselFreeze) || !s.writeFloat(takeCompMode) || !s.writeFloat(takeCompPhraseLength) || !s.writeFloat(memoryFollowPlayhead) || !s.writeFloat(memoryRecallTake)) return kResultFalse;
    if(memoryCursorKey<std::numeric_limits<int32>::min() || memoryCursorKey>std::numeric_limits<int32>::max()) return kResultFalse;
    if(!s.writeInt32(static_cast<int32>(memoryCursorKey)) || !s.writeFloat(smartRankMode) || !s.writeFloat(personalTasteEnable) || !s.writeFloat(personalTasteStrength) || !s.writeFloat(personalTasteLearn) || !s.writeFloat(preferenceMinConfidence) || !s.writeFloat(preferenceMinMargin) || !s.writeFloat(preferenceSafetyFloor)) return kResultFalse;
    if(!s.writeFloat(stageMixerEnable)||!s.writeFloat(stageMasterGain)||!s.writeFloat(stageOutputGain))return kResultFalse;
    for(float g:stageFeedGain)if(!s.writeFloat(g))return kResultFalse;
    std::array<PersistentTakeCompEntry,PersistentPhraseTakeComp::kCapacity> compEntries{};
    const int compCount=phraseTakeComp.exportEntries(compEntries);
    if(!s.writeInt32(static_cast<int32>(compCount))) return kResultFalse;
    for(int i=0;i<compCount;++i){
        const auto& e=compEntries[static_cast<std::size_t>(i)];
        if(e.phraseKey<std::numeric_limits<int32>::min() || e.phraseKey>std::numeric_limits<int32>::max()) return kResultFalse;
        if(!s.writeInt32(static_cast<int32>(e.phraseKey)) || !s.writeInt32(static_cast<int32>(e.takeIndex)) ||
           !s.writeInt32(static_cast<int32>(e.favoriteMask)) || !s.writeInt32(static_cast<int32>(e.rejectMask)) ||
           !s.writeInt32(e.committed ? 1 : 0)) return kResultFalse;
    }
    for (const auto& c : part) {
        const float v[] = {c.dyn,c.vib,c.exp,c.vol,c.pan,c.sus,c.leg,c.room,c.bend,c.art,c.transition,c.tightness,c.attack,c.speedProfile};
        for (float x : v) if (!s.writeFloat(x)) return kResultFalse;
    }
    return kResultOk;
}

} // namespace Sonicraft::AIStrings
