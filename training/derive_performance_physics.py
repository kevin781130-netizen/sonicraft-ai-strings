from __future__ import annotations
"""Derive conservative physical transition labels from RIGHTS-CLEARED aligned monophonic data.

Expected NPZ inputs (at a common control-frame rate):
  pitch                  intended MIDI pitch curve
  f0_midi                measured/estimated performed pitch in MIDI units
  onset                  note-on impulse curve
  tempo_bpm              frame-wise BPM
  articulation_curve     0..11 (1=legato, 2=portamento)
Optional:
  rms                    frame-wise RMS/energy
  spectral_centroid      normalized/Hz centroid curve
  bow_change_marker      explicit trusted bow-change marker
  fps                    scalar frame rate; otherwise --fps is used

The script intentionally does NOT infer commercial permissions. The index is passed through
source_policy.validate_index before any derived labels are emitted. Derived masks remain 0 if
confidence is too low, so uncertain analysis cannot silently become supervision.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from source_policy import validate_index


def _last_true(x):
    z=np.flatnonzero(x); return int(z[-1]) if len(z) else None

def _first_true(x):
    z=np.flatnonzero(x); return int(z[0]) if len(z) else None

def analyze_transition(pitch,f0,onset,arts,bpm,fps):
    n=len(pitch);out={k:np.zeros(n,np.float32) for k in (
        'transition_duration_ms','transition_physics_known',
        'legato_transition_beats','legato_overlap_ratio','legato_attack_suppression','legato_continuity',
        'legato_transition_known','legato_overlap_known','legato_attack_known','legato_continuity_known','legato_physics_known',
        'portamento_transition_beats','portamento_slide_extent_ratio','portamento_curve_shape','portamento_arrival_softness',
        'portamento_transition_known','portamento_slide_extent_known','portamento_curve_shape_known','portamento_arrival_softness_known','portamento_physics_known')}
    onset_idx=np.flatnonzero(onset>.5)
    for j in onset_idx:
        if j<2 or j>=n-2: continue
        old=float(np.median(pitch[max(0,j-3):j]));new=float(np.median(pitch[j:min(n,j+3)]));interval=new-old
        if abs(interval)<.25: continue
        radius=max(3,int(round(.45*fps)));a=max(0,j-radius);b=min(n,j+radius)
        seg=f0[a:b]
        voiced=np.isfinite(seg)&(seg>0)
        if voiced.sum()<max(4,int(.15*fps)): continue
        old_ok=voiced & (np.abs(seg-old)<.18); new_ok=voiced & (np.abs(seg-new)<.18)
        pre=_last_true(old_ok[:max(1,j-a+1)])
        post0=_first_true(new_ok[max(0,j-a):])
        if pre is None or post0 is None: continue
        st=a+pre; en=j+post0
        if en<=st: continue
        dur_ms=(en-st)*1000.0/fps
        if dur_ms<8 or dur_ms>500: continue
        beat_ms=60000.0/max(24.0,min(240.0,float(np.median(bpm[max(st,0):min(en+1,n)]))))
        beats=dur_ms/beat_ms
        art=int(round(float(np.median(arts[max(j-1,0):min(j+2,n)]))))
        out['transition_duration_ms'][j]=dur_ms;out['transition_physics_known'][j]=1
        # Pitch travel coverage: 1 means the observed transition spans the intended interval.
        travel=float(np.nanmax(seg[voiced])-np.nanmin(seg[voiced])) if voiced.any() else 0.
        extent=min(1.5,max(0.,travel/max(abs(interval),1e-3)))
        if art==2:
            # Timing, pitch-travel extent and curve crossing are directly derived from measured F0.
            # Arrival softness is NOT invented: it stays unsupervised unless a later importer provides
            # a trustworthy acoustic/annotation measurement.
            out['portamento_transition_beats'][j]=beats; out['portamento_transition_known'][j]=1
            out['portamento_slide_extent_ratio'][j]=min(1.,extent)
            if extent>.30: out['portamento_slide_extent_known'][j]=1
            mid=(old+new)/2.; local=f0[st:en+1]; good=np.isfinite(local)
            cross=np.flatnonzero(good & ((local-mid)*np.sign(interval)>=0))
            if len(cross):
                frac=cross[0]/max(1,len(local)-1)
                out['portamento_curve_shape'][j]=float(np.clip(frac,0,1)); out['portamento_curve_shape_known'][j]=1
            out['portamento_physics_known'][j]=max(out['portamento_transition_known'][j],out['portamento_slide_extent_known'][j],out['portamento_curve_shape_known'][j])
        elif art==1:
            # Only transition timing is defensibly observable from this minimal F0 alignment.
            # Do not fabricate overlap, attack suppression or continuity targets.
            out['legato_transition_beats'][j]=beats; out['legato_transition_known'][j]=1
            out['legato_physics_known'][j]=1
    return out


def analyze_bow(npz,n,bpm,fps):
    out={k:np.zeros(n,np.float32) for k in (
        'bow_change_duration_ms','bow_change_beats','bow_change_strength','bow_brightness_delta','bow_continuity',
        'bow_timing_known','bow_strength_known','bow_brightness_known','bow_continuity_known','bow_physics_known')}
    if 'bow_change_marker' not in npz.files: return out
    mark=np.asarray(npz['bow_change_marker'],float)>0.5
    rms=np.asarray(npz['rms'],float) if 'rms' in npz.files else None
    cen=np.asarray(npz['spectral_centroid'],float) if 'spectral_centroid' in npz.files else None
    for j in np.flatnonzero(mark):
        r=max(2,int(round(.08*fps)));a=max(0,j-r);b=min(n,j+r+1)
        dur_ms=None; strength=0.; bright=0.; continuity=0.
        if rms is not None and b-a>=3:
            loc=rms[a:b];med=float(np.median(loc))+1e-7
            dip=float(np.clip((med-float(np.min(loc)))/med,0,1));strength=dip;continuity=1.-.65*dip
            out['bow_change_strength'][j]=strength; out['bow_strength_known'][j]=1
            out['bow_continuity'][j]=continuity; out['bow_continuity_known'][j]=1
            threshold=med*(1-.35*max(.05,dip));inds=np.flatnonzero(loc<threshold)
            if len(inds):
                dur_ms=max(8.,min(140.,(inds[-1]-inds[0]+1)*1000./fps))
                beat_ms=60000./max(24.,min(240.,float(bpm[j])))
                out['bow_change_duration_ms'][j]=dur_ms; out['bow_change_beats'][j]=dur_ms/beat_ms; out['bow_timing_known'][j]=1
        if cen is not None and b-a>=3:
            loc=cen[a:b];base=float(np.median(loc))+1e-7
            bright=float(np.clip((float(loc[min(j-a,len(loc)-1)])-base)/base,-1,1))
            out['bow_brightness_delta'][j]=bright; out['bow_brightness_known'][j]=1
        out['bow_physics_known'][j]=max(out['bow_timing_known'][j],out['bow_strength_known'][j],out['bow_brightness_known'][j],out['bow_continuity_known'][j])
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--index',required=True);ap.add_argument('--out-dir',required=True);ap.add_argument('--out-index',required=True)
    ap.add_argument('--fps',type=float,default=100.0);ap.add_argument('--registry',default='training/dataset_registry.json')
    a=ap.parse_args();validate_index(a.index,a.registry);outdir=Path(a.out_dir);outdir.mkdir(parents=True,exist_ok=True)
    rows=[json.loads(x) for x in Path(a.index).read_text(encoding='utf-8').splitlines() if x.strip()];new=[]
    for ri,r in enumerate(rows):
        d=np.load(r['file']);keys={k:d[k] for k in d.files};n=len(np.asarray(d['pitch']))
        fps=float(np.asarray(d['fps']).reshape(-1)[0]) if 'fps' in d.files else a.fps
        if 'f0_midi' in d.files and 'onset' in d.files:
            pitch=np.asarray(d['pitch'],float);f0=np.asarray(d['f0_midi'],float);on=np.asarray(d['onset'],float)
            arts=np.asarray(d['articulation_curve'] if 'articulation_curve' in d.files else np.full(n,int(d['articulation'])),float)
            bpm=np.asarray(d['tempo_bpm'] if 'tempo_bpm' in d.files else np.full(n,68),float)
            keys.update(analyze_transition(pitch,f0,on,arts,bpm,fps));keys.update(analyze_bow(d,n,bpm,fps))
        dst=outdir/(Path(r['file']).stem+'_physics_v07.npz');np.savez_compressed(dst,**keys)
        rr=dict(r);rr['file']=str(dst);rr['derived_physics']='v0.7 conservative aligned analysis';new.append(rr)
    Path(a.out_index).parent.mkdir(parents=True,exist_ok=True);Path(a.out_index).write_text('\n'.join(json.dumps(x) for x in new)+'\n',encoding='utf-8')
    print('derived',len(new),'segments ->',a.out_index)
if __name__=='__main__':main()
