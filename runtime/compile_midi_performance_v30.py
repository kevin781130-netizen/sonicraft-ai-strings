"""SONICRAFT v3.0 host-intelligent compiler.

Builds the editable v2.9 Q4 MIDI, then injects a self-describing Performance Command Lane
snapshot so the MIDI itself configures SONICRAFT's assist/director/authority behavior in a DAW.
"""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, sys
from compile_midi_performance_v29 import compile_file as compile_v29, PARTS
from project_bridge_v30 import apply_snapshot, DEFAULTS, COMMAND_CCS

def _stable_note_id(n):
    s=f'{n.track}|{n.channel}|{n.start}|{n.end}|{n.note}|{n.order}'
    return 'scn_'+hashlib.sha1(s.encode()).hexdigest()[:16]

def compile_file(src:Path,out:Path|None=None,manifest:Path|None=None,emit_cc=True,emit_keyswitch=True,takes=8):
    out=out or src.with_name(src.stem+'_SONICRAFT_Q4_v30.mid')
    manifest=manifest or out.with_suffix('.performance.json')
    tmp=out.with_suffix('.v29tmp.mid'); tmpman=manifest.with_suffix('.v29tmp.json')
    try:
        _,_,notes=compile_v29(src,tmp,tmpman,emit_cc,emit_keyswitch,takes)
        apply_snapshot(tmp,out,DEFAULTS,True)
        d=json.loads(tmpman.read_text(encoding='utf-8'))
        d['schema']=2; d['sonicraft_version']='3.0.0-host-intelligence-bridge'
        d['output_midi']=str(out)
        d['host_command_lane']={
            'transport':'MIDI CC','scope':'global parameters duplicated to Q4 part tracks for single-plugin or four-instance routing',
            'cc_map':COMMAND_CCS,'snapshot':DEFAULTS,
            'region_bridge':'runtime/project_bridge_v30.py',
            'principle':'performance commands are patchable without rewriting notes or authored conventional CC lanes',
        }
        for row,n in zip(d.get('notes',[]),notes): row['note_id']=_stable_note_id(n)
        manifest.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        tmp.unlink(missing_ok=True); tmpman.unlink(missing_ok=True)
    return out,manifest,notes

def main(argv=None):
    ap=argparse.ArgumentParser(description='Compile ordinary MIDI into SONICRAFT v3.0 host-intelligent Q4 MIDI.')
    ap.add_argument('midi',type=Path); ap.add_argument('-o','--out',type=Path); ap.add_argument('--manifest',type=Path); ap.add_argument('--no-cc',action='store_true'); ap.add_argument('--no-keyswitch',action='store_true'); ap.add_argument('--takes',type=int,default=8)
    a=ap.parse_args(argv)
    try:o,m,notes=compile_file(a.midi,a.out,a.manifest,not a.no_cc,not a.no_keyswitch,a.takes)
    except Exception as e: print(f'ERROR: {e}',file=sys.stderr); return 2
    print('SONICRAFT v3.0 host-intelligent compile OK'); print('MIDI:',o); print('Manifest:',m); print('Notes:',len(notes)); return 0
if __name__=='__main__': raise SystemExit(main())
