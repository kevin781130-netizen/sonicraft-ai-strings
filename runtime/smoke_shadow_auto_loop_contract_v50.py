from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
shadow=(ROOT/'runtime/shadow_render_auto_v50.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v50.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v50.py').read_text()
ids=(ROOT/'src/ids.h').read_text();proc=(ROOT/'src/processor.cpp').read_text();ctl=(ROOT/'src/controller.cpp').read_text();cm=(ROOT/'CMakeLists.txt').read_text()

# Must use existing Renderer Service protocol, not direct backend invocation.
for token in ['TYPE_RENDER','pack_request_header','socket.create_connection','start_shadow_service_v50','renderer_service.py','render_midi_v50']:
    assert token in shadow,token
assert 'from model_backend import' not in shadow
assert 'from ort_model_backend import' not in shadow

# Full string-control mapping into existing Shadow opcodes.
for token in ['PHYS={27:112,28:113,29:114,30:115,31:116,33:117,34:118,35:119}',
              'ENSEMBLE={36:120,37:121}','GESTURE={38:122}','cc==39','KS_BASE','_packed(base_art[ch],stack[ch])']:
    assert token in shadow,token

# Long-file chunking stays below Renderer Service 45 s cap and carries the full event buffer per request.
assert 'max(5.0,min(44.0,float(chunk_seconds)))' in shadow
assert 'DEFAULT_CHUNK_SECONDS=40.0' in shadow and 'DEFAULT_OVERLAP_SECONDS=.75' in shadow
assert "raw=b''.join(_pack_event(e) for e in events)" in shadow
assert 'np.linspace(0,1,m' in shadow and 'np.linspace(1,0,m' in shadow

# Loop actually compiles, renders all A/B/C/D, judges, learns, and regenerates.
for token in ['compile_file(score,out,policy_path,round_index)','for si,slot in enumerate(SLOTS)',
              'render_midi_v50','judge_take','mem.learn(winner,margin,ws.safety,ws.overall)',
              "'review_required'","'round_cap'","label='WINNER' if accepted else 'REVIEW_BEST'","_SONICRAFT_STRINGS_v50_{label}",
              '_SONICRAFT_STRINGS_v50_DECISION_TRACE.json']:
    assert token in loop,token
assert 'MAX_ROUND=6' in loop

# v5.0 compiler marks queue as auto-loop capable.
for token in ['"version":"5.0"','"shadow_auto_loop"','"supported":True','AUTO_LOOP_STRINGS_v50.bat']:
    assert token in comp,token

# No new realtime state/control family.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n);seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl
assert any(x in cm for x in ['VERSION 5.0.0','VERSION 5.1.0','VERSION 5.2.0','VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0']) and 'SonicraftStringShadowAutoLoopSmokeV50' in cm

for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1','installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['shadow_render_auto_v50.py','compile_musicxml_strings_v50.py','auto_loop_strings_v50.py']:
        assert token in text,(rel,token)
assert 'AUTO_LOOP_STRINGS_v50.bat' in (ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
assert 'Tools/AUTO_LOOP_STRINGS_v50.bat' in (ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()
print('SONICRAFT v5.0 Local Shadow Render Auto-Loop source contract OK')
