from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
from source_policy import validate_index
from vibrato_calibration import VibratoCalibration

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--index',required=True);ap.add_argument('--calibration',required=True)
    ap.add_argument('--out-dir',required=True);ap.add_argument('--out-index',required=True);ap.add_argument('--registry',default='training/dataset_registry.json')
    a=ap.parse_args();validate_index(a.index,a.registry);cal=VibratoCalibration.load(a.calibration);od=Path(a.out_dir);od.mkdir(parents=True,exist_ok=True)
    rows=[]
    for line in Path(a.index).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        r=json.loads(line);d=np.load(r['file']);keys={k:d[k] for k in d.files};n=len(d['pitch']);inst=str(int(np.asarray(d['instrument']).reshape(-1)[0]))
        depth=np.asarray(d['vibrato_depth_cents'] if 'vibrato_depth_cents' in d.files else np.zeros(n),float)
        known=np.asarray(d['vibrato_depth_known'] if 'vibrato_depth_known' in d.files else (d['vibrato_known'] if 'vibrato_known' in d.files else np.zeros(n)),float)>.5
        vib=np.asarray(d['vibrato'] if 'vibrato' in d.files else np.zeros(n),np.float32).copy()
        for i in np.flatnonzero(known): vib[i]=cal.depth_to_cc3(float(depth[i]),inst)
        keys['vibrato']=vib.astype(np.float32);keys['vibrato_calibrated_known']=known.astype(np.float32)
        dst=od/(Path(r['file']).stem+'_vibcal_v08.npz');np.savez_compressed(dst,**keys)
        rr=dict(r);rr['file']=str(dst);rr['vibrato_calibration']=str(Path(a.calibration));rows.append(rr)
    p=Path(a.out_index);p.parent.mkdir(parents=True,exist_ok=True);p.write_text('\n'.join(json.dumps(x) for x in rows)+'\n',encoding='utf-8')
    print('applied calibrated CC3 to',len(rows),'segments ->',p)
if __name__=='__main__': main()
