from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from source_policy import validate_index
from performance_timing import TimingCalibration, DEFAULT_BEAT_PRIORS

FAMILY_BY_ART={1:'legato',2:'portamento'}
QUANTILES={'fast':.20,'normal':.50,'slow':.80}

def main():
    ap=argparse.ArgumentParser(description='Fit beat-domain Slow/Normal/Fast timing anchors from rights-cleared aligned transitions.')
    ap.add_argument('--index',required=True);ap.add_argument('--out',default='checkpoints/timing_calibration_v07.json')
    ap.add_argument('--registry',default='training/dataset_registry.json');ap.add_argument('--min-events',type=int,default=20)
    a=ap.parse_args(); validate_index(a.index,a.registry)
    rows=[json.loads(x) for x in Path(a.index).read_text(encoding='utf-8').splitlines() if x.strip()]
    buckets={}
    accepted=0
    for r in rows:
        d=np.load(r['file'])
        if 'transition_duration_ms' not in d.files or 'tempo_bpm' not in d.files: continue
        known=np.asarray(d['transition_physics_known'] if 'transition_physics_known' in d.files else np.zeros_like(d['tempo_bpm']),float)>0.5
        if not known.any(): continue
        bpm=np.asarray(d['tempo_bpm'],float); dur=np.asarray(d['transition_duration_ms'],float)
        arts=np.asarray(d['articulation_curve'] if 'articulation_curve' in d.files else np.full_like(bpm,int(d['articulation'])),int)
        inst=int(d['instrument'])
        valid=known & np.isfinite(bpm)&np.isfinite(dur)&(bpm>20)&(dur>5)
        for fam_art,fam in FAMILY_BY_ART.items():
            m=valid & (arts==fam_art)
            if not m.any(): continue
            beats=dur[m]/(60000.0/bpm[m])
            key=(fam,str(inst)); buckets.setdefault(key,[]).extend(beats.tolist()); accepted+=int(m.sum())
        # Optional dedicated bow-change labels can occur under any articulation.
        if 'bow_change_duration_ms' in d.files and 'bow_physics_known' in d.files:
            bm=np.asarray(d['bow_timing_known'] if 'bow_timing_known' in d.files else d['bow_physics_known'],float)>0.5; bdur=np.asarray(d['bow_change_duration_ms'],float)
            valid2=bm & np.isfinite(bpm)&np.isfinite(bdur)&(bpm>20)&(bdur>3)
            if valid2.any():
                beats=bdur[valid2]/(60000.0/bpm[valid2]);buckets.setdefault(('bow_change',str(inst)),[]).extend(beats.tolist());accepted+=int(valid2.sum())
    out={fam:{'all':dict(v)} for fam,v in DEFAULT_BEAT_PRIORS.items()}
    for (fam,inst),xs in buckets.items():
        arr=np.asarray(xs,float)
        if len(arr)<a.min_events: continue
        out.setdefault(fam,{})[inst]={name:float(np.quantile(arr,q)) for name,q in QUANTILES.items()}
    # Also fit pooled 'all' if enough events exist.
    for fam in DEFAULT_BEAT_PRIORS:
        pooled=[x for (f,i),xs in buckets.items() if f==fam for x in xs]
        if len(pooled)>=a.min_events:
            arr=np.asarray(pooled,float);out.setdefault(fam,{})['all']={name:float(np.quantile(arr,q)) for name,q in QUANTILES.items()}
    cal=TimingCalibration(out,accepted,1);cal.save(a.out)
    print('timing calibration saved',a.out,'accepted_frames',accepted)
    for fam,tab in out.items(): print(fam,tab)
if __name__=='__main__':main()
