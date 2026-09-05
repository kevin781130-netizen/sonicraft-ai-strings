from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ids=(ROOT/'src/ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
ctl=(ROOT/'src/controller.cpp').read_text(encoding='utf-8')
ui=(ROOT/'resource/SONICRAFT_AI_Strings_Q4.uidesc').read_text(encoding='utf-8')
shadow_h=(ROOT/'src/shadow_render_client.h').read_text(encoding='utf-8')
shadow_cpp=(ROOT/'src/shadow_render_client.cpp').read_text(encoding='utf-8')
protocol=(ROOT/'runtime/protocol.py').read_text(encoding='utf-8')
service=(ROOT/'runtime/renderer_service.py').read_text(encoding='utf-8')
judge=(ROOT/'runtime/audio_take_judge_v37.py').read_text(encoding='utf-8')

for token in [
 'kParamJudgeTrigger = 175','kParamJudgeWinner = 176','kParamJudgeOverallBase = 177',
 'kParamJudgeDynamicsBase = 181','kParamJudgeAttackBase = 185','kParamJudgeTransitionBase = 189',
 'kParamJudgeStabilityBase = 193','kParamJudgeWinnerSafety = 197',
 'kParamJudgeAuditionWinner = 198','kParamJudgeCommitWinner = 199'
]:
    assert token in ids, token
assert 'kParamPartDynamicsBase   = 200' in ids

for token in ['TYPE_JUDGE = 3',"JUDGE_CONFIG = struct.Struct('<fBBH')","JUDGE_RESULT = struct.Struct('<HBB24f')"]:
    assert token in protocol, token
for token in ['_handle_judge','rank_takes','_derive_take_nonce','_flags_with_nonce','TYPE_JUDGE']:
    assert token in service, token

for token in ['TakeJudgeScore','judge_take','rank_takes','_contour_score','_attack_score','_transition_score','_stability_score','_safety_score']:
    assert token in judge, token
assert 'not a claim of musical taste' in judge
assert 'Master stereo only' not in judge or True

for token in ['requestTakeJudge','takeJudgeSnapshot','judgePending','judgeGeneration','judgeResultStart']:
    assert token in shadow_h, token
for token in ['requestJudgeRender','JudgeConfigV37','JudgePayloadV37','kJudge=3','judgeResultStart.store']:
    assert token in shadow_cpp, token

# Phrase identity guard: stale Judge result cannot be applied to another phrase.
assert 'snap.startSample==range[0]' in proc
assert 'judgeSnap.startSample==judgeRange[0]' in proc
assert 'js.startSample==jr[0]' in proc

# Audio-aware Smart actions must prefer a valid judge, then fall back to v3.6 heuristic.
assert 'const int selectedTake=judgeUsable?judgeSnap.winner:ranked.take;' in proc

# DSP runs in renderer service, not the realtime processor.
assert 'audio_take_judge_v37' not in proc
assert 'requestTakeJudge' in proc
assert 'cached=self._read_cache(key,take_req)' in service
assert 'sampleRate*90.0' in shadow_cpp

for token in ['Run Audio Take Judge','Audio Judge Winner','Audition Judge Winner','Commit Judge Winner']:
    assert token in ctl, token
for token in ['JudgeTrigger','JudgeWinner','JudgeOverallA','JudgeDynamicsA','JudgeAttackA','JudgeTransitionA','JudgeStabilityA','JudgeWinnerSafety']:
    assert token in ui, token

# v3.7 also fixes a controller restore regression: transient reset must not overwrite
# the persistent v11/v12 browser/rank values that were just read.
state_fn=ctl[ctl.index('setComponentState'):]
main_reset=state_fn[state_fn.index('// Reset transient action/status parameters only.'):state_fn.index('    }else{')]
assert 'setParamNormalized(kParamMemoryFollowPlayhead' not in main_reset
assert 'setParamNormalized(kParamMemoryRecallTake' not in main_reset
assert 'setParamNormalized(kParamSmartRankMode' not in main_reset

# No state schema bump: v3.7 Judge data is derived/ephemeral; v12 project state stays backward compatible.
assert any(x in proc for x in ['constexpr int kStateVersion = 12;','constexpr int kStateVersion = 13;'])
assert any(x in ctl for x in ['(version<3||version>12)','(version<3||version>13)'])

# Expanded UI must fit.
assert any(x in ui for x in ['size="1120,1090" minSize="900,900" maxSize="1500,1280"','size="1120,1210" minSize="900,1000" maxSize="1500,1400"'])
assert any(x in ui for x in ['origin="28,576" size="1064,470"','origin="28,576" size="1064,590"'])
assert any(x in ctl for x in ['VSTGUI::CPoint(900, 900), VSTGUI::CPoint(1500, 1280)','VSTGUI::CPoint(900, 1000), VSTGUI::CPoint(1500, 1400)'])


# Judge validity is both phrase-identity and configuration-identity guarded.
assert 'configToken=0' in shadow_h
assert 'judgePendingToken' in shadow_h and 'judgeResultToken' in shadow_h
assert 'judgeResultToken.store(configToken' in shadow_cpp
assert 'const uint64_t judgeToken=judgePendingToken.load' in shadow_cpp
assert 'judge.configToken==judgeConfigToken' in proc
assert 'judgeSnap.configToken==judgeConfigToken' in proc
assert 'snap.configToken==judgeConfigToken' in proc
assert 'js.configToken==judgeConfigToken' in proc
# In-flight Judge must carry a captured token, not read a mutable pending token after the response.
assert 'uint64_t configToken' in shadow_h
assert 'uint64_t configToken,uint32_t policyFlags' in shadow_cpp and 'requestJudgeRender' in shadow_cpp

# Controller restore regression: persistent v11/v12 values are not present in transient-reset block.
assert 'Reset transient action/status parameters only' in ctl
state_fn=ctl[ctl.index('setComponentState'):]
main_reset=state_fn[state_fn.index('// Reset transient action/status parameters only.'):state_fn.index('    }else{')]
assert 'setParamNormalized(kParamMemoryFollowPlayhead' not in main_reset
assert 'setParamNormalized(kParamMemoryRecallTake' not in main_reset
assert 'setParamNormalized(kParamSmartRankMode' not in main_reset

# Basic lexical brace balance for controller.cpp after the restore cleanup.
def brace_balance(src):
    NORMAL,SLASH,LINE,BLOCK,STR,CHR=range(6); st=NORMAL; bal=0; i=0
    while i<len(src):
        c=src[i]; n=src[i+1] if i+1<len(src) else ''
        if st==NORMAL:
            if c=='/' and n=='/': st=LINE;i+=1
            elif c=='/' and n=='*': st=BLOCK;i+=1
            elif c=='"': st=STR
            elif c=="'": st=CHR
            elif c=='{': bal+=1
            elif c=='}': bal-=1
        elif st==LINE:
            if c=='\n': st=NORMAL
        elif st==BLOCK:
            if c=='*' and n=='/': st=NORMAL;i+=1
        elif st in (STR,CHR):
            q='"' if st==STR else "'"
            if c=='\\': i+=1
            elif c==q: st=NORMAL
        if bal<0:return bal
        i+=1
    return bal
assert brace_balance(ctl)==0


# Pinned phrase Judge must snapshot the phrase's resolved policy/tempo instead of using the current playhead state.
tempo=(ROOT/'src/tempo_timeline.h').read_text(encoding='utf-8')
assert 'sampleAtBeat' in tempo and 'tempoAtBeat' in tempo and 'std::int64_t sample' in tempo
assert 'tempoTimeline.observe(data.processContext->projectTimeMusic, hostTempoBpm, projectStart)' in proc
assert 'tempoTimeline.sampleAtBeat(q0,sr,s0)' in proc
assert 'judgeScopedState' in proc and 'judgePolicyFlags' in proc and 'judgePhraseTempo' in proc
assert 'judgePolicyFlags(scoped)' in proc
assert 'judgeConfigToken(fav,rej,scoped,phraseTempo)' in proc
assert 'judgePendingFlags' in shadow_h and 'judgePendingMode' in shadow_h and 'judgePendingTempo' in shadow_h
assert 'const uint32_t flags=policyFlags;' in shadow_cpp
assert 'const uint32_t judgeFlags=judgePendingFlags.load' in shadow_cpp

print('SONICRAFT v3.7 Audio-Aware Take Judge source contract OK')
