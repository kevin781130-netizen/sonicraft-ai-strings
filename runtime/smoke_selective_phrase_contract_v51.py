from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
search=(ROOT/'runtime/selective_phrase_search_v51.py').read_text()
local=(ROOT/'runtime/shadow_render_selective_v51.py').read_text()
merge=(ROOT/'runtime/selective_midi_merge_v51.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v51.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v51.py').read_text()
ids=(ROOT/'src/ids.h').read_text()
proc=(ROOT/'src/processor.cpp').read_text()
ctl=(ROOT/'src/controller.cpp').read_text()
cm=(ROOT/'CMakeLists.txt').read_text()

# Search must combine critic evidence with lower-weight repair locations and explicit fallbacks.
for token in ['build_selective_plan_v51','_severity_weight','_dimension_weight','_latent_risk',
              'problem_coverage_too_large','too_many_problem_windows','critic_location_mapping_incomplete',
              'score[key]+=.15','coverage_limit=.55','max_windows=6']:
    assert token in search,token

# Local Shadow render must send full history into existing TCP render request while requesting an
# absolute context range. Judge gets the unfaded core.
for token in ['compiled_midi_to_shadow_events_v50','_render_request(events,render_start,render_end',
              'core=x[ia:ib].copy()','_audition_fade(core','MAX_LOCAL_CONTEXT_SECONDS=28.0']:
    assert token in local,token

# MIDI merge is D-based, channel-only and boundary guarded.
for token in ['base_midi','candidate_midis','_patch_event','Conductor/meta data remains from D',
              'tick==end','_is_note_off','_is_cc','_is_keyswitch_on']:
    assert token in merge,token
assert 'if slot=="D":continue' in merge

# Loop must do selective local A/B/C/D, candidate-specific Judge, mixed-winner policy aggregation,
# full fallback on any ambiguous local window, then one final full render of merged MIDI.
for token in [
    'build_selective_plan_v51','render_midi_window_v51','judge_take(r["audio"]',
    'splice_midi_windows_v51','_aggregate_local_learning','DOMINANCE_FLOOR=.60',
    'local_low_margin_W','local_safety_floor_W','local_low_overall_W',
    '_full_fallback_round','render_midi_v50(merged,merged_wav',
    'local_render_equivalent_full','estimated_total_vs_four_full_fraction'
]:
    assert token in loop,token

# v5.1 compiler advertises selective capability.
for token in ['"version":"5.1"','"selective_phrase_search"','"coverage_fallback":.55',
              'AUTO_LOOP_STRINGS_v51.bat']:
    assert token in comp,token

# No realtime control/state expansion.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n);seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl
assert any(x in cm for x in ['VERSION 5.1.0','VERSION 5.2.0','VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftSelectivePhraseSmokeV51' in cm

for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['selective_phrase_search_v51.py','shadow_render_selective_v51.py','selective_midi_merge_v51.py',
                  'compile_musicxml_strings_v51.py','auto_loop_strings_v51.py']:
        assert token in text,(rel,token)
assert 'AUTO_LOOP_STRINGS_v51.bat' in (ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
assert 'Tools/AUTO_LOOP_STRINGS_v51.bat' in (ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()

print('SONICRAFT v5.1 Selective Phrase Local Repair source contract OK')
