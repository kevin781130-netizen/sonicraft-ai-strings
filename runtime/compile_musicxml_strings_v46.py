"""SONICRAFT v4.6 Continuous Transition & Legato Path Compiler.

v4.6 keeps the v4.5 MIDI control vocabulary. The important change is graph topology:
connected bowed notes on one explicit String Voice lane share one continuous CC38 gesture window.
That lets the HQ renderer interpolate through note boundaries and infer a true continuous pitch
conditioning path from the written notes, without adding another CC/ParamID family.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,struct,sys

from score_expression_graph_v40 import parse_score,graph_dict,PARTS,PPQ
from compile_musicxml_strings_v41 import allocate_voice_lanes,VOICE_CHANNELS,_cc,_stack_cc,_tempo_meta,_time_meta,_key_meta,KS_BASE
from compile_midi_performance_v29 import _track_bytes,_name_event,_meta
from string_physical_graph_v42 import plan_string_physics,physical_note_dict
from string_constraint_solver_v43 import solve_string_constraints
from string_ensemble_solver_v44 import coordinate_string_ensemble
from string_ensemble_runtime_v44 import attack_norm_from_ms,breath_norm_from_ms
from string_gesture_graph_v45 import plan_continuous_string_gestures,gesture_note_dict
from string_gesture_runtime_v45 import micro_pitch_norm_from_cents
from string_transition_graph_v46 import build_continuous_transition_graph_v46,transition_graph_dict

def _marker(text:str):return _meta(0x06,text.encode('utf-8','replace')[:220])

def _phys_cc_values(n):
    return {27:_cc((max(0,min(3,n.string_index))/3.0)*127.0),28:_cc((max(0,min(8,n.position_index))/8.0)*127.0),
            29:127 if int(n.bow_direction)==1 else 0,30:127 if n.bow_change else 0,31:_cc(float(n.bow_pressure)*127.0),
            33:_cc(float(n.contact_point)*127.0),34:_cc(float(n.portamento_route)*127.0),35:_cc((max(0,min(3,n.divisi_desk))/3.0)*127.0)}

def _gesture_events_v46(n,ch):
    if not n.gesture_anchors or n.gesture_amount<=0:return []
    out=[];dur=max(1,n.end_tick-n.start_tick);pre=max(0,n.start_tick-max(1,PPQ//96))
    # A connected phrase opens CC38 only on its first note and closes it only on its last.
    if not n.transition_in_link_id:
        out.append((pre,2,bytes([0xB0|ch,38,_cc(n.gesture_amount*127.0)])))
        out.append((pre,2,bytes([0xB0|ch,39,64])))
    else:
        # Updating a non-zero CC38 while active can only raise amount; runtime keeps one phrase window.
        out.append((pre,2,bytes([0xB0|ch,38,_cc(n.gesture_amount*127.0)])))

    for a in n.gesture_anchors:
        tick=min(n.end_tick-1,n.start_tick+int(round(float(a['u'])*dur)))
        tick=max(n.start_tick,tick)
        energy=float(a['dynamics_energy']);vib=float(a['vibrato_depth']);porta=float(a['portamento'])
        pressure=float(a['bow_pressure']);contact=float(a['contact_point']);bow_speed=float(a['bow_speed']);kinetic=float(a['kinetic_response'])
        trans=.50-porta*.22+(bow_speed-.5)*.035
        attack=.38+(bow_speed-.5)*.16+(kinetic-.5)*.12
        micro=micro_pitch_norm_from_cents(float(a['micro_pitch_cents']))
        for cc,val in [(22,energy),(23,vib),(24,trans),(25,attack),(31,pressure),(33,contact),(34,porta),(39,micro)]:
            out.append((tick,2,bytes([0xB0|ch,cc,_cc(val*127.0)])))

    if not n.transition_out_link_id:
        out.append((n.end_tick,4,bytes([0xB0|ch,38,0])))
        out.append((n.end_tick,4,bytes([0xB0|ch,39,64])))
    return out

def write_midi(g,constraints,ensemble,links,out:Path):
    conductor=[(0,0,_name_event('SONICRAFT v4.6 Continuous Transition Strings'))]
    conductor += [(x['tick'],1,_tempo_meta(x['bpm'])) for x in g.tempos]
    conductor += [(x['tick'],1,_time_meta(x['numerator'],x['denominator'])) for x in g.time_signatures]
    conductor += [(x['tick'],1,_key_meta(x['fifths'])) for x in g.key_signatures]
    sev={'error':0,'warning':1,'info':2}
    for issue in sorted(constraints.issues,key=lambda x:(x.tick,sev.get(x.severity,9),x.kind)):
        conductor.append((max(0,int(issue.tick)),3,_marker(f'SONICRAFT {issue.severity.upper()} {PARTS[issue.part]}: {issue.kind}')))
    for issue in sorted(ensemble.issues,key=lambda x:(x.tick,sev.get(x.severity,9),x.kind)):
        conductor.append((max(0,int(issue.tick)),3,_marker(f'SONICRAFT ENSEMBLE {issue.severity.upper()}: {issue.kind}')))
    for link in links:
        if link.warnings:
            conductor.append((max(0,int(link.to_tick)),4,_marker(f'SONICRAFT TRANSITION {PARTS[link.part]}: {link.mode} / {",".join(link.warnings)}')))

    tracks=[_track_bytes(conductor)]
    global_cmd=[(0,0,bytes([0xB0,117,127])),(0,0,bytes([0xB0,112,0])),(0,0,bytes([0xB0,114,127])),(0,0,bytes([0xB0,109,127])),(0,0,bytes([0xB0,110,127]))]
    for p,name in enumerate(PARTS):
        ev=[(0,0,_name_event('SONICRAFT '+name+' · v4.6 Continuous Transition Voice Bus'))]
        if p==0:ev+=global_cmd
        for n in sorted((x for x in g.notes if x.part==p),key=lambda x:(x.start_tick,x.lane_channel,x.pitch)):
            ch=n.lane_channel;pre=max(0,n.start_tick-max(1,PPQ//96))
            ev.append((pre,1,bytes([0x90|ch,KS_BASE+n.base_art,1])));ev.append((n.start_tick,0,bytes([0x80|ch,KS_BASE+n.base_art,0])))
            ev.append((pre,2,bytes([0xB0|ch,21,_stack_cc(n.stack)])));ev.append((pre,2,bytes([0xB0|ch,22,_cc(n.cc1)])));ev.append((pre,2,bytes([0xB0|ch,23,_cc(n.cc3)])))
            transition=64-(12 if n.stack&2 else 0)-(5 if n.stack&4 else 0)-int(round(n.portamento_route*18))-int(round(min(1.0,n.transition_risk)*8))
            if n.transition_in_link_id:
                transition-=int(round(max(0.0,min(1.0,n.transition_continuity))*9))
            attack=48+(22 if n.stack&1 else 0)-(12 if n.stack&8 else 0)+int(round((n.bow_pressure-.5)*16+(n.contact_point-.5)*12))
            tight=64+(10 if n.stack&1 else 0)-(20 if n.stack&4 else 0)+int(round((n.contact_point-.5)*12))
            ev += [(pre,2,bytes([0xB0|ch,24,_cc(transition)])),(pre,2,bytes([0xB0|ch,25,_cc(attack)])),(pre,2,bytes([0xB0|ch,26,_cc(tight)]))]
            for cc,val in _phys_cc_values(n).items():ev.append((pre,2,bytes([0xB0|ch,cc,val])))
            ev.append((pre,2,bytes([0xB0|ch,36,_cc(attack_norm_from_ms(n.ensemble_attack_offset_ms)*127.0)])))
            ev.append((pre,2,bytes([0xB0|ch,37,_cc(breath_norm_from_ms(n.ensemble_breath_ms)*127.0)])))
            ev += _gesture_events_v46(n,ch)
            ev.append((n.start_tick,3,bytes([0x90|ch,n.pitch,max(1,min(127,n.velocity))])));ev.append((n.end_tick,0,bytes([0x80|ch,n.pitch,0])))
        tracks.append(_track_bytes(ev))
    hdr=b'MThd'+struct.pack('>IHHH',6,1,len(tracks),PPQ)
    out.write_bytes(hdr+b''.join(b'MTrk'+struct.pack('>I',len(tr))+tr for tr in tracks))

def compile_file(src:Path,out:Path|None=None,score_json:Path|None=None,constraints_json:Path|None=None,ensemble_json:Path|None=None,gesture_json:Path|None=None,transition_json:Path|None=None):
    g=allocate_voice_lanes(parse_score(src))
    plan_string_physics(g)
    g,constraints=solve_string_constraints(g)
    g,ensemble=coordinate_string_ensemble(g)
    g=plan_continuous_string_gestures(g)
    g,links=build_continuous_transition_graph_v46(g)

    out=out or src.with_name(src.stem+'_SONICRAFT_STRINGS_v46.mid')
    score_json=score_json or out.with_suffix('.score.json')
    constraints_json=constraints_json or out.with_suffix('.constraints.json')
    ensemble_json=ensemble_json or out.with_suffix('.ensemble.json')
    gesture_json=gesture_json or out.with_suffix('.gesture.json')
    transition_json=transition_json or out.with_suffix('.transition.json')
    write_midi(g,constraints,ensemble,links,out)

    data=graph_dict(g);gestures=[gesture_note_dict(n) for n in g.notes if n.gesture_amount>0]
    data.update({
        'sonicraft_version':'4.6','compiled_midi':out.name,
        'continuous_transition':{
            'link_count':len(links),
            'new_midi_cc_or_paramids':False,
            'phrase_window_contract':'CC38 stays non-zero across connected notes',
            'hq_pitch_path':True,
            'vibrato_envelope_continuity':True,
            'pressure_contact_energy_continuity':True,
            'legacy_v45_single_note_windows_unchanged':True,
        },
        'physical_notes':[{'source_id':n.source_id,**physical_note_dict(n),
                           'gesture_profile':n.gesture_profile,'gesture_amount':round(float(n.gesture_amount),6),
                           'transition_in_link_id':n.transition_in_link_id,'transition_out_link_id':n.transition_out_link_id,
                           'transition_in_mode':n.transition_in_mode,'transition_out_mode':n.transition_out_mode,
                           'transition_duration_ms':round(float(n.transition_duration_ms),6),
                           'transition_continuity':round(float(n.transition_continuity),6),
                           'transition_flags':list(n.transition_flags)} for n in g.notes],
        'string_voice_bus':{'voices_per_part':4,'total_lanes':16,'channels':{PARTS[p]:[x+1 for x in VOICE_CHANNELS[p]] for p in range(4)}}
    })
    score_json.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    constraints_json.write_text(json.dumps(constraints.as_dict(),ensure_ascii=False,indent=2),encoding='utf-8')
    ensemble_json.write_text(json.dumps(ensemble.as_dict(),ensure_ascii=False,indent=2),encoding='utf-8')
    gesture_json.write_text(json.dumps({'schema':1,'version':'4.6','gesture_notes':gestures},ensure_ascii=False,indent=2),encoding='utf-8')
    transition_json.write_text(json.dumps(transition_graph_dict(links),ensure_ascii=False,indent=2),encoding='utf-8')
    return out,score_json,constraints_json,ensemble_json,gesture_json,transition_json,g,constraints,ensemble,links

def main(argv=None):
    ap=argparse.ArgumentParser(description='Compile MusicXML/MXL with SONICRAFT v4.6 Continuous Transition & Legato Paths.')
    ap.add_argument('score',type=Path);ap.add_argument('-o','--out',type=Path);a=ap.parse_args(argv)
    try:o,s,c,e,gj,tj,g,cr,er,links=compile_file(a.score,a.out)
    except Exception as ex:print('ERROR:',ex,file=sys.stderr);return 2
    print('SONICRAFT v4.6 Continuous Transition & Legato Compile OK')
    print('MIDI:',o);print('Transition:',tj);print('notes:',len(g.notes),'links:',len(links));return 0
if __name__=='__main__':raise SystemExit(main())
