from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--index',required=True); ap.add_argument('--out',default='reports/control_coverage.json'); a=ap.parse_args()
    rows=[json.loads(x) for x in Path(a.index).read_text(encoding='utf-8').splitlines() if x.strip()]
    keys=['dynamics_known','vibrato_known','vibrato_depth_known','vibrato_rate_known','vibrato_onset_known','vibrato_jitter_known','expression_known','legato_known','pitchbend_known','timing_known','articulation_known','transition_physics_known','legato_physics_known','portamento_physics_known','bow_physics_known']
    counts={k:[0,0] for k in keys}; sources={}; vib_bins={'straight':0,'light':0,'natural':0,'deep':0,'intense':0}; vib_frames=0
    for r in rows:
        d=np.load(r['file']); src=str(r.get('dataset','unknown')); sources[src]=sources.get(src,0)+1
        for k in keys:
            arr=d[k] if k in d.files else np.array([0.],dtype=np.float32); counts[k][0]+=float(arr.mean()); counts[k][1]+=1
        if 'vibrato' in d.files:
            vib=np.asarray(d['vibrato'],dtype=np.float32); known=np.asarray(d['vibrato_depth_known'],dtype=np.float32) if 'vibrato_depth_known' in d.files else (np.asarray(d['vibrato_known'],dtype=np.float32) if 'vibrato_known' in d.files else np.zeros_like(vib))
            vals=vib[known>.5]
            for x in vals:
                q=float(x)*127.0
                if q<16:vib_bins['straight']+=1
                elif q<48:vib_bins['light']+=1
                elif q<80:vib_bins['natural']+=1
                elif q<112:vib_bins['deep']+=1
                else:vib_bins['intense']+=1
            vib_frames+=int(len(vals))
    report={'segments':len(rows),'sources':sources,'mean_supervision_coverage':{k:(v[0]/max(1,v[1])) for k,v in counts.items()},
            'cc3_anchor_frame_distribution':vib_bins,'cc3_supervised_frames':vib_frames}
    p=Path(a.out); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
