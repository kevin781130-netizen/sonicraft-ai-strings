from pathlib import Path
import re
from project_bridge_v30 import COMMAND_CCS, DEFAULTS
root=Path(__file__).resolve().parents[1]
h=(root/'src/host_command_lane_v30.h').read_text(); c=(root/'src/controller.cpp').read_text()
cpp={name:int(val) for name,val in re.findall(r'kCC_([A-Za-z0-9_]+)\s*=\s*(\d+)',h)}
expected={
 'AIAssist':'ai_assist','PerformanceStyle':'performance_style','SmartDynamics':'smart_dynamics','SmartArticulation':'smart_articulation',
 'RetakeTarget':'retake_target','RetakeAmount':'retake_amount','RetakeSeed':'retake_seed','MidiAuthorityLock':'midi_authority_lock',
 'PhraseDirector':'phrase_director','EnsembleLooseness':'ensemble_looseness','AutoDivisi':'auto_divisi','StagePerspective':'stage_perspective',
 'IndependentPolyphony':'independent_polyphony','AIMix':'ai_mix','AILookAhead':'ai_lookahead','LayoutMode':'layout_mode',
 'SingleInstrument':'single_instrument','Humanize':'humanize'}
assert set(expected)==set(cpp), (set(expected)^set(cpp))
for ck,pk in expected.items():
    assert cpp[ck]==COMMAND_CCS[pk], (ck,cpp[ck],COMMAND_CCS[pk]); assert f'case kCC_{ck}:' in c, f'VST mapping missing kCC_{ck}'
assert sorted(COMMAND_CCS.values())==list(range(102,120))
assert DEFAULTS['layout_mode']==1 and DEFAULTS['auto_divisi']==0 and DEFAULTS['midi_authority_lock']==1
print('SONICRAFT v3.0 Python/C++/VST command contract smoke OK')
