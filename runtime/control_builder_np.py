"""Pure NumPy control builder shared by the v2.2 no-PyTorch ORT challenger.

It mirrors the public runtime control contract without importing torch. The existing Torch
backend remains untouched until parity tests on trained checkpoints pass.
"""
from __future__ import annotations
import math,hashlib
import numpy as np
from instrument_x_cleanroom import decode_flags,predictive_dynamics,smart_articulation_curve,apply_targeted_retake,articulation_stack_modifiers,phrase_director_curve
from string_physical_runtime_v42 import physical_curves,apply_string_physical_residuals
from string_ensemble_runtime_v44 import apply_ensemble_event_timing_v44
from string_gesture_runtime_v45 import smooth_voice_controls_v45,smooth_physical_curves_v45
from string_transition_runtime_v46 import apply_continuous_transition_paths_v46
from string_phrase_runtime_v47 import apply_phrase_longline_v47
from quartet_interaction import coordinate_hidden_ensemble
from frontier_context import frontier_context_curves

RAW_NAMES=(
 'pitch','gate','onset','velocity','dynamics','vibrato','expression','legato','pitchbend',
 'transition_speed','short_tightness','attack_character','note_progress','phrase_position',
 'prev_interval','next_interval','bow_change_prob','vibrato_onset','tempo_bpm','seconds_per_beat',
 'note_duration_beats','transition_target_ms','speed_profile','vibrato_depth_cents','vibrato_rate_hz',
 'vibrato_jitter','dynamics_known','vibrato_known','expression_known','legato_known',
 'pitchbend_known','timing_known','articulation_known')
_EXPRESSIVE_ZERO={
 'dynamics','vibrato','expression','legato','pitchbend','transition_speed','short_tightness','attack_character',
 'bow_change_prob','vibrato_onset','tempo_bpm','seconds_per_beat','note_duration_beats','transition_target_ms',
 'speed_profile','vibrato_depth_cents','vibrato_rate_hz','vibrato_jitter','dynamics_known','vibrato_known',
 'expression_known','legato_known','pitchbend_known','timing_known'}

def build_part_controls_np(req,events,part,fingerprint='ort-v22',fps=100,context_events=None):
    sr=float(req.sample_rate);dur=max(.08,(req.end_sample-req.start_sample)/sr);N=max(8,int(math.ceil(dur*fps)))
    # v2.7 dual-source contract: authored note/CC controls come from the monophonic
    # lane, while quartet/phrase context sees the full ensemble timeline.
    ctx_events=events if context_events is None else context_events
    pitch=np.zeros(N,np.float32);gate=np.zeros(N,np.float32);onset=np.zeros(N,np.float32);vel=np.full(N,.7,np.float32)
    dyn=np.full(N,.62,np.float32);vib=np.full(N,.50,np.float32);exp=np.full(N,.90,np.float32);leg=np.ones(N,np.float32)
    pb=np.full(N,.50,np.float32);trans=np.full(N,.50,np.float32);tight=np.full(N,.50,np.float32);attack=np.full(N,.38,np.float32);speed=np.zeros(N,np.float32)
    art=np.zeros(N,np.int64);expr_stack=np.zeros(N,np.uint8);notes=[];active=None
    pe=[e for e in sorted(events,key=lambda x:x['project_sample']) if int(e.get('part',-1))==part or int(e.get('type',0))==5]
    pe=apply_ensemble_event_timing_v44(pe,sr)
    for e in pe:
        ps=int(e['project_sample']);before=ps<int(req.start_sample);idx=int(max(0,min(N-1,round((ps-req.start_sample)/sr*fps))))
        c=e.get('controls') or [.62,.5,.9,.86,.5,1,1,.18,.5,0,.5,.5,.38,0]
        dyn[idx:]=c[0];vib[idx:]=c[1];exp[idx:]=c[2];leg[idx:]=c[6];pb[idx:]=c[8];art[idx:]=int(round(c[9]*11));trans[idx:]=c[10];tight[idx:]=c[11];attack[idx:]=c[12];speed[idx:]=c[13]
        packed=int(e.get('articulation',0));base_art=packed&0x0F;stack_bits=(packed>>4)&0x0F
        if int(e['type']) in (1,3,4):
            if 0<=base_art<12:art[idx:]=base_art
            expr_stack[idx:]=stack_bits
        if int(e['type'])==1:
            if active is not None:active['off']=idx;active['off_sample']=ps
            active={'note':int(e['note']),'on':0 if before else idx,'off':N,'vel':float(e['velocity']),
                    'preexisting':before,'on_sample':ps,'off_sample':int(req.end_sample)};notes.append(active)
        elif int(e['type'])==2 and active is not None and active['note']==int(e['note']):
            active['off']=max(active['on'],idx);active['off_sample']=ps;active=None
    dyn,vib,exp,leg,pb,trans,tight,attack,speed=smooth_voice_controls_v45(
        pe,req.start_sample,req.end_sample,sr,fps,(dyn,vib,exp,leg,pb,trans,tight,attack,speed))
    for n in notes:
        a,b=n['on'],min(N,n['off'])
        if b>a:pitch[a:b]=n['note'];gate[a:b]=1.;vel[a:b]=n['vel'];onset[a:min(N,a+2)]=0 if n.get('preexisting') else 1
    note_prog=np.zeros(N,np.float32);dur_beats=np.zeros(N,np.float32);prev_int=np.zeros(N,np.float32);next_int=np.zeros(N,np.float32)
    for j,n in enumerate(notes):
        a,b=n['on'],min(N,n['off']);L=max(1,b-a);note_prog[a:b]=np.linspace(0,1,L,endpoint=False,dtype=np.float32);dur_beats[a:b]=(L/fps)*max(24.,float(req.tempo_bpm))/60.
        if j:prev_int[a:b]=float(n['note']-notes[j-1]['note'])
        if j+1<len(notes):next_int[a:b]=float(notes[j+1]['note']-n['note'])
    phrase=np.linspace(0,1,N,dtype=np.float32);policy=decode_flags(int(req.flags));assist=(0.,.6,1.)[policy.assist_level]
    dyn=predictive_dynamics(dyn,pitch,gate,onset,note_prog,phrase,prev_int,next_int,float(req.tempo_bpm),policy)
    art=smart_articulation_curve(art,gate,onset,dur_beats,leg,prev_int,next_int,float(req.tempo_bpm),policy)
    dyn,attack,tight,trans=articulation_stack_modifiers(art,dyn,attack,tight,trans,policy,expr_stack)
    bow=np.clip(onset*(.18+.37*assist)+(1-leg)*onset*(.10+.25*assist),0,1).astype(np.float32);vib_on=np.zeros(N,np.float32)
    bow,vib_on=coordinate_hidden_ensemble(bow,vib_on,gate,onset,ctx_events,part,req.start_sample,req.end_sample,sr,assist,fps=fps)
    if policy.ensemble_looseness>0:
        phase=(part+1)*1.61803398875
        drift=np.sin(np.linspace(0,6.2831853,N,dtype=np.float32)+phase)*(.035*policy.ensemble_looseness)
        bow=np.clip(bow+drift,0,1);vib_on=np.clip(vib_on-drift*.55,0,1)
    frontier_ctx,phrase=frontier_context_curves(ctx_events,part,req.start_sample,req.end_sample,sr,float(req.tempo_bpm),dyn,vib,leg,fps=fps)
    bpm=np.full(N,float(req.tempo_bpm),np.float32);spb=np.full(N,60/max(24.,float(req.tempo_bpm)),np.float32)
    z=np.zeros(N,np.float32);ones=np.ones(N,np.float32);trans_ms=np.zeros(N,np.float32)
    dyn,attack,trans,vib_on=phrase_director_curve(dyn,attack,trans,vib_on,phrase,note_prog,next_int,gate,policy)
    phys=physical_curves(pe,req.start_sample,sr,fps,N)
    phys=smooth_physical_curves_v45(phys,pe,req.start_sample,req.end_sample,sr,fps)
    if phys is not None:
        dyn,vib,exp,leg,trans,tight,attack,bow,pb=apply_string_physical_residuals(
            dyn,vib,exp,leg,trans,tight,attack,bow,pb,phys,gate,onset)
    porta_curve=None if phys is None else phys.get(118)
    pitch,gate,onset,note_prog,leg,trans,vib,vib_on,pb,trans_ms,_transition_links=apply_continuous_transition_paths_v46(
        notes,pitch,gate,onset,note_prog,leg,trans,vib,vib_on,pb,pe,
        req.start_sample,req.end_sample,sr,fps,porta_curve)
    dyn,vib,exp,attack,tight,bow,vib_on,vib_depth_cents,vib_rate_hz,phrase_momentum,_phrase_windows=apply_phrase_longline_v47(
        dyn,vib,exp,attack,tight,bow,vib_on,pe,req.start_sample,req.end_sample,sr,fps)
    lane_id=next((int(e.get('voice_lane',-1)) for e in pe if int(e.get('voice_lane',-1))>=0),-1)
    retake_identity=part if lane_id<0 else part+4*(lane_id+1)
    ret=apply_targeted_retake({'dynamics':dyn,'attack_character':attack,'short_tightness':tight,'bow_change_prob':bow,'vibrato_onset':vib_on,'vibrato_jitter':z.copy(),'pitchbend':pb,'transition_speed':trans,'timing_feel':z.copy()},fingerprint,retake_identity,policy)
    dyn=ret['dynamics'];attack=ret['attack_character'];tight=ret['short_tightness'];bow=ret['bow_change_prob'];vib_on=ret['vibrato_onset'];vj=ret['vibrato_jitter'];pb=ret['pitchbend'];trans=ret['transition_speed']
    vals=dict(pitch=pitch,gate=gate,onset=onset,velocity=vel,dynamics=dyn,vibrato=vib,expression=exp,legato=leg,pitchbend=pb,
              transition_speed=trans,short_tightness=tight,attack_character=attack,note_progress=note_prog,phrase_position=phrase,
              prev_interval=prev_int,next_interval=next_int,bow_change_prob=bow,vibrato_onset=vib_on,tempo_bpm=bpm,seconds_per_beat=spb,
              note_duration_beats=dur_beats,transition_target_ms=trans_ms,speed_profile=speed,vibrato_depth_cents=vib_depth_cents,vibrato_rate_hz=vib_rate_hz,vibrato_jitter=vj,
              dynamics_known=ones,vibrato_known=ones,expression_known=ones,legato_known=ones,pitchbend_known=ones,timing_known=z,articulation_known=ones)
    raw=np.stack([np.asarray(vals[n],np.float32) for n in RAW_NAMES],axis=-1)[None]
    ins=0 if part<2 else (1 if part==2 else 2)
    return {'raw':raw,'vibrato_physics_known':(vib_rate_hz>0).astype(np.float32)[None],'frontier_context':np.asarray(frontier_ctx,np.float32)[None],
            'instrument':np.asarray([ins],np.int64),'articulation':np.asarray([int(art[0])],np.int64),'player':np.asarray([part],np.int64),
            'articulation_curve':art.astype(np.float32)[None],'gate':gate,'policy':policy}

def midi_authority_base_np(c):
    out={k:(v.copy() if isinstance(v,np.ndarray) else v) for k,v in c.items()}
    raw=out['raw'].copy()
    for name in _EXPRESSIVE_ZERO:raw[...,RAW_NAMES.index(name)]=0
    out['raw']=raw;out['vibrato_physics_known']=np.zeros_like(out['vibrato_physics_known']);out['frontier_context']=np.zeros_like(out['frontier_context'])
    return out
