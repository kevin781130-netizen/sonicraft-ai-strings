from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ids=(ROOT/'src/ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
ctl=(ROOT/'src/controller.cpp').read_text(encoding='utf-8')
expr=(ROOT/'src/string_expression_v41.h').read_text(encoding='utf-8')
poly=(ROOT/'runtime/polyphony.py').read_text(encoding='utf-8')
service=(ROOT/'runtime/renderer_service.py').read_text(encoding='utf-8')
cb=(ROOT/'runtime/control_builder_np.py').read_text(encoding='utf-8')
mb=(ROOT/'runtime/model_backend.py').read_text(encoding='utf-8')
compiler=(ROOT/'runtime/compile_musicxml_strings_v41.py').read_text(encoding='utf-8')

for token in ['kParamVoiceStackBase = 400','kParamVoiceDynamicsBase = 420','kParamVoiceVibratoBase = 440',
              'kParamVoiceTransitionBase = 460','kParamVoiceAttackBase = 480','kParamVoiceTightnessBase = 500']:
    assert token in ids,token
for token in ['stringPartForMidiChannel','packArticulationExpression','applyStringExpressionModifiers','encodeShadowStringPart']:
    assert token in expr,token
for token in ['decodeVoiceParam','mergedVoiceControl','engine.noteOnVoice','engine.noteOffVoice','encodeShadowStringPart']:
    assert token in proc,token
for cc in range(21,27):
    assert f'case {cc}:' in ctl
assert 'channel>=16' in ctl
assert "voice_lane" in service
assert "explicit=[e for e in pe if int(e.get('voice_lane',-1))>=0" in poly
assert "global_controls=[e for e in pe if int(e.get('type',0))==5" in poly
assert 'expression_stack' in (ROOT/'runtime/instrument_x_cleanroom.py').read_text(encoding='utf-8')
assert 'expr_stack' in cb and 'packed=int(e.get(' in cb
assert 'expr_stack' in mb
for token in ['VOICE_CHANNELS','String Voice Bus','string_voice_lane_overflow']:
    assert token in compiler,token
assert 'bytes([0xB0|ch,21' in compiler and 'bytes([0xB0|ch,26' in compiler
# Legacy Q4 channels remain exactly 0,1,2,3 for first voice.
assert '0:(0,4,5,6)' in compiler and '1:(1,7,8,9)' in compiler and '2:(2,10,11,12)' in compiler and '3:(3,13,14,15)' in compiler
# No new acoustic articulation IDs: packed high nibble is control stack, low nibble remains base.
assert 'packed&0x0F' in cb and '(packed>>4)&0x0F' in cb

# Installer/prebuilt must include the score compiler and its dependency.
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    s=(ROOT/rel).read_text(encoding='utf-8')
    for mod in ['score_expression_graph_v40.py','compile_musicxml_strings_v41.py','compile_midi_performance_v29.py']:
        assert mod in s,(rel,mod)
assert 'COMPILE_MUSICXML_STRINGS_v41.bat' in (ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text(encoding='utf-8')
assert 'Tools/COMPILE_MUSICXML_STRINGS_v41.bat' in (ROOT/'installer/tools/verify_prebuilt_layout.py').read_text(encoding='utf-8')

# Explicit ParamID ranges must not overlap any legacy/public explicit numeric IDs.
import re
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n)
    seen[v]=n
voice_ranges=[range(400,416),range(420,436),range(440,456),range(460,476),range(480,496),range(500,516)]
vals=set()
for r in voice_ranges:
    for v in r:
        assert v not in vals
        vals.add(v)
assert all(v>363 for v in vals)

# State schema intentionally remains v13 because per-note state lives in MIDI/Score Graph.
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl

print('SONICRAFT v4.1 strings per-note voice-bus source contract OK')
