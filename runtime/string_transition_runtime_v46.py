"""SONICRAFT v4.6 phrase-level continuous transition runtime.

A v4.6 link is identified without a new CC: one CC38 gesture window remains open across the
note boundary. v4.5 closes CC38 at every note, so legacy gesture notes do not enter this path.

For linked boundaries the HQ control builder:
- suppresses a redundant new-note onset impulse,
- creates a short continuous pitch-conditioning trajectory between the written pitches,
- carries legato/transition intent through the boundary,
- exposes transition_target_ms to the existing physical-performance expert,
- interprets CC39 as true lane-local +/-50-cent pitch conditioning inside multi-note windows.

The MIDI pitches remain unchanged and the effect is renderer conditioning only.
"""
from __future__ import annotations
import numpy as np
from string_gesture_runtime_v45 import gesture_windows_v45,GESTURE_MAX_MICRO_CENTS

def _sample_in_window(ps,windows):
    return any(a<=int(ps)<=b for a,b,_ in windows)

def _spans_boundary(boundary_sample,windows,margin=1):
    return any(a<int(boundary_sample)-margin and b>int(boundary_sample)+margin for a,b,_ in windows)

def multi_note_gesture_active_v46(events,start_sample,end_sample):
    windows=gesture_windows_v45(events,start_sample,end_sample)
    if not windows:return False
    note_ons=sorted(int(e.get("project_sample",0)) for e in events if int(e.get("type",0))==1)
    for a,b,_ in windows:
        if sum(1 for ps in note_ons if a<=ps<b)>=2:return True
    return False

def apply_micro_pitch_conditioning_v46(pitch,pitchbend,events,start_sample,end_sample,sr,fps):
    """Fix v4.5's ambiguous pitch-bend scaling only for v4.6 multi-note phrase windows.

    CC39 is defined as +/-50 cents. In a v4.6 phrase window it is converted directly into the
    float MIDI-pitch conditioning curve, then pitchbend is re-centered so no second scaling occurs.
    """
    if not multi_note_gesture_active_v46(events,start_sample,end_sample):
        return pitch,pitchbend
    p=np.asarray(pitch,np.float32).copy()
    pb=np.asarray(pitchbend,np.float32).copy()
    windows=gesture_windows_v45(events,start_sample,end_sample)
    n=len(p)
    for a,b,_ in windows:
        ia=int(max(0,min(n-1,round((a-start_sample)/float(sr)*fps))))
        ib=int(max(ia+1,min(n,round((b-start_sample)/float(sr)*fps)+1)))
        cents=(pb[ia:ib]-.5)*(2.0*GESTURE_MAX_MICRO_CENTS)
        p[ia:ib]+=cents/100.0
        pb[ia:ib]=.5
    return p,pb

def apply_continuous_transition_paths_v46(
    notes,pitch,gate,onset,note_prog,leg,trans,vib,vib_on,pitchbend,events,
    start_sample,end_sample,sr,fps,portamento_curve=None
):
    pitch=np.asarray(pitch,np.float32).copy();gate=np.asarray(gate,np.float32).copy()
    onset=np.asarray(onset,np.float32).copy();note_prog=np.asarray(note_prog,np.float32).copy()
    leg=np.asarray(leg,np.float32).copy();trans=np.asarray(trans,np.float32).copy()
    vib=np.asarray(vib,np.float32).copy();vib_on=np.asarray(vib_on,np.float32).copy()
    pb=np.asarray(pitchbend,np.float32).copy()
    target_ms=np.zeros_like(pitch,dtype=np.float32)
    windows=gesture_windows_v45(events,start_sample,end_sample)
    if not windows or len(notes)<2:
        return pitch,gate,onset,note_prog,leg,trans,vib,vib_on,pb,target_ms,0

    links=0
    porta=np.asarray(portamento_curve,np.float32) if portamento_curve is not None else None
    for prev,nxt in zip(notes,notes[1:]):
        boundary_sample=int(nxt.get("on_sample",start_sample))
        if not _spans_boundary(boundary_sample,windows):continue
        a=int(prev["on"]);off=int(prev["off"]);b=int(nxt["on"]);end=int(nxt["off"])
        if b<0 or b>=len(pitch) or off<0:continue
        # A phrase window crossing the boundary is the v4.6 authoring contract.
        local_leg=max(float(leg[max(0,b-1)]),float(leg[min(len(leg)-1,b)]))
        local_porta=0.0 if porta is None else max(float(porta[max(0,b-1)]),float(porta[min(len(porta)-1,b)]))
        if max(local_leg,local_porta)<.35:continue

        interval=float(nxt["note"]-prev["note"])
        explicit_porta=local_porta>.42
        # 100-fps transition window: fast legato 20-50ms; explicit portamento can be 60-180ms.
        if explicit_porta:
            ms=max(55.0,min(180.0,55.0+abs(interval)*7.0+(1.0-float(trans[b]))*28.0))
        else:
            ms=max(18.0,min(60.0,22.0+abs(interval)*2.4+(1.0-float(trans[b]))*12.0))
        frames=max(2,int(round(ms*.001*fps)))
        left=max(a,b-frames//2);right=min(end,b+(frames-frames//2))
        if right-left<2:continue

        # Smoothstep written-pitch trajectory. This is the actual cross-note pitch path for HQ.
        x=np.linspace(0.0,1.0,right-left,endpoint=True,dtype=np.float32)
        s=x*x*(3.0-2.0*x)
        pitch[left:right]=float(prev["note"])+(float(nxt["note"])-float(prev["note"]))*s

        # One physical gesture: avoid retriggering a second hard attack.
        onset[b:min(len(onset),b+2)]=0.0
        leg[left:right]=np.maximum(leg[left:right],.92 if explicit_porta else .82)
        trans[left:right]=np.minimum(trans[left:right],.32 if explicit_porta else .42)
        target_ms[left:right]=np.float32(ms)

        # Keep note-progress away from a hard zero reset during the transition head.
        head=min(end,b+max(2,frames//2))
        if head>b:
            note_prog[b:head]=np.maximum(note_prog[b:head],np.linspace(.12,.30,head-b,dtype=np.float32))

        # Carry vibrato envelope depth through the fingering change; do not force a new bloom.
        if b>0 and b<len(vib):
            boundary_vib=(float(vib[b-1])+float(vib[b]))*.5
            lo=max(0,b-2);hi=min(len(vib),b+3)
            vib[lo:hi]=np.maximum(vib[lo:hi],boundary_vib*.88)
            vib_on[lo:hi]=np.minimum(vib_on[lo:hi],.08)

        links+=1

    pitch,pb=apply_micro_pitch_conditioning_v46(pitch,pb,events,start_sample,end_sample,sr,fps)
    return pitch,gate,onset,note_prog,leg,trans,vib,vib_on,pb,target_ms,links
