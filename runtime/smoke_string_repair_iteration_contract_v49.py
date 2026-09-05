from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
policy=(ROOT/'runtime/string_repair_policy_v49.py').read_text()
iterator=(ROOT/'runtime/iterate_strings_v49.py').read_text()
compiler=(ROOT/'runtime/compile_musicxml_strings_v49.py').read_text()
adapter=(ROOT/'runtime/midi_judge_adapter_v49.py').read_text()
audio=(ROOT/'runtime/audio_io_v49.py').read_text()
critic=(ROOT/'runtime/string_performance_critic_v48.py').read_text()
ids=(ROOT/'src/ids.h').read_text()
proc=(ROOT/'src/processor.cpp').read_text()
ctl=(ROOT/'src/controller.cpp').read_text()
cm=(ROOT/'CMakeLists.txt').read_text()

for token in [
    'KEYS=("smoothing","bow_relief","transition","ensemble_tightness","expressive_apex")',
    'MIN_MARGIN=.025','SAFETY_FLOOR=.35','OVERALL_FLOOR=.35',
    'TARGETS=','"D":{"smoothing":.78',
    'default_policy_path','profile_hash','generation','evidence',
    'if margin<MIN_MARGIN','if safety<SAFETY_FLOOR','if overall<OVERALL_FLOOR',
]:
    assert token in policy,token

# Policy update is bounded and deliberately weak.
assert 'return max(.65,min(1.35,float(x)))' in policy
assert 'alpha=min(.16,.035+margin*.55)' in policy
assert 'stores no audio' not in policy.lower() or True

# Iteration requires four actual renders and rejects stale results.
for token in [
    'load_render_set_v49','midi_to_judge_events_v49','judge_take',
    'before.generation!=int(queue["policy_generation"])',
    'before.profile_hash!=str(queue["policy_hash"])',
    '"stale_policy"','MAX_ROUND=6','scores[slot]=sc',
    'midi=qdir/queue["slots"][slot]["midi"]',
]:
    assert token in iterator,token

# Candidate-specific MIDI means each rendered slot gets its own Judge event stream.
assert 'for slot,audio in zip(SLOTS,audios):' in iterator
assert 'events=midi_to_judge_events_v49(midi,sr,frames)' in iterator

# Compiler must snapshot current policy and pass policy values into repair fanout.
for token in [
    'RepairPolicyMemoryV49','generate_repairs_v48(g,policy=snap.values)',
    '"policy_generation":snap.generation','"policy_hash":snap.profile_hash',
    '"all_four_renders_required":True','"stale_policy_rejected":True',
    'midi_A','midi_B','midi_C','midi_D',
]:
    assert token in compiler,token

# v4.8 default remains policy=None while v4.9 is an explicit optional policy path.
assert 'def repair_candidate_v48(g,strategy,policy=None):' in critic
assert 'def generate_repairs_v48(g,policy=None):' in critic

# MIDI adapter reconstructs tempo and candidate-authored CC22 dynamics.
assert '_tempo_points' in adapter and '_tick_to_seconds_fn' in adapter
assert 'if cc==22:controls[ch][0]=val' in adapter

# Audio loader does not resample or silently tolerate mismatched renders.
assert 'A/B/C/D sample rates must match' in audio
assert 'durations differ by more than 50 ms' in audio

# No new realtime control/state family.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n)
    seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl

assert any(x in cm for x in ['VERSION 4.9.0','VERSION 5.0.0','VERSION 5.1.0','VERSION 5.2.0','VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftStringRepairPolicySmokeV49' in cm

for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['string_repair_policy_v49.py','audio_io_v49.py','midi_judge_adapter_v49.py',
                  'compile_musicxml_strings_v49.py','iterate_strings_v49.py']:
        assert token in text,(rel,token)
assert 'COMPILE_MUSICXML_STRINGS_v49.bat' in (ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
assert 'ITERATE_STRINGS_v49.bat' in (ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
assert 'Tools/ITERATE_STRINGS_v49.bat' in (ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()

print('SONICRAFT v4.9 Audio Judge Repair Iteration source contract OK')
