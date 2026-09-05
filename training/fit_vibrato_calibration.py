from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
from source_policy import validate_index
from vibrato_calibration import VibratoCalibration, DEFAULT_DEPTH, DEFAULT_RATE

DEPTH_Q=(.20,.50,.75,.92)
RATE_Q=(.20,.50,.80)
ONSET_Q=(.25,.50,.75)

def runs(mask):
    m=np.asarray(mask,bool);i=0
    while i<len(m):
        if not m[i]: i+=1;continue
        j=i+1
        while j<len(m) and m[j]: j+=1
        yield i,j;i=j

def collect(index,min_conf):
    out={}
    rows=[json.loads(x) for x in Path(index).read_text(encoding='utf-8').splitlines() if x.strip()]
    for r in rows:
        d=np.load(r['file']); n=len(d['pitch']); inst=str(int(np.asarray(d['instrument']).reshape(-1)[0]))
        known=np.asarray(d['vibrato_depth_known'] if 'vibrato_depth_known' in d.files else (d['vibrato_known'] if 'vibrato_known' in d.files else np.zeros(n)),float)>.5
        conf=np.asarray(d['vibrato_confidence'] if 'vibrato_confidence' in d.files else np.ones(n),float)
        known &= conf>=min_conf
        depth=np.asarray(d['vibrato_depth_cents'] if 'vibrato_depth_cents' in d.files else np.zeros(n),float)
        rate=np.asarray(d['vibrato_rate_hz'] if 'vibrato_rate_hz' in d.files else np.zeros(n),float)
        onset=np.asarray(d['vibrato_onset_ms'] if 'vibrato_onset_ms' in d.files else np.zeros(n),float)
        rate_known=np.asarray(d['vibrato_rate_known'] if 'vibrato_rate_known' in d.files else known,float)>.5
        onset_known=np.asarray(d['vibrato_onset_known'] if 'vibrato_onset_known' in d.files else known,float)>.5
        for a,b in runs(known):
            rec=out.setdefault(inst,{'depth':[],'rate':[],'onset':[]})
            dd=float(np.nanmedian(depth[a:b]));
            if np.isfinite(dd): rec['depth'].append(dd)
            rr=rate[a:b][rate_known[a:b]]
            if len(rr): rec['rate'].append(float(np.nanmedian(rr)))
            oo=onset[a:b][onset_known[a:b]]
            if len(oo): rec['onset'].append(float(np.nanmedian(oo)))
    return out

def fit_vals(xs,qs,defaults,lo,hi,min_n):
    a=np.asarray([x for x in xs if np.isfinite(x) and lo<=x<=hi],float)
    if len(a)<min_n: return list(defaults),len(a)
    return [float(np.quantile(a,q)) for q in qs],len(a)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--index',required=True);ap.add_argument('--out',default='checkpoints/vibrato_calibration_v08.json')
    ap.add_argument('--registry',default='training/dataset_registry.json');ap.add_argument('--min-events',type=int,default=12);ap.add_argument('--min-confidence',type=float,default=.58)
    a=ap.parse_args();validate_index(a.index,a.registry);raw=collect(a.index,a.min_confidence)
    pooled={'depth':[],'rate':[],'onset':[]}
    for v in raw.values():
        for k in pooled: pooled[k]+=v[k]
    depth_rows={};rate_rows={};onset_rows={};counts={}
    for key,v in [('all',pooled),*sorted(raw.items())]:
        nonzero=[x for x in v['depth'] if x>=4.0]
        d,n=fit_vals(nonzero,DEPTH_Q,DEFAULT_DEPTH[1:],4,90,a.min_events)
        anchors=[0.0]+d
        # enforce a useful four-layer spacing even when real data are clustered
        for i in range(1,5): anchors[i]=max(anchors[i], [0,6,12,20,30][i], anchors[i-1]+3)
        depth_rows[key]=anchors
        rr,nr=fit_vals(v['rate'],RATE_Q,[DEFAULT_RATE['slow'],DEFAULT_RATE['normal'],DEFAULT_RATE['fast']],3.5,8.5,a.min_events)
        rate_rows[key]={'slow':rr[0],'normal':rr[1],'fast':rr[2]}
        oo,no=fit_vals(v['onset'],ONSET_Q,[140,250,390],30,900,a.min_events)
        onset_rows[key]={'early':oo[0],'natural':oo[1],'late':oo[2]}
        counts[key]={'depth_events':n,'rate_events':nr,'onset_events':no}
    cal=VibratoCalibration(depth_rows,rate_rows,onset_rows,counts,1);cal.save(a.out)
    print('vibrato calibration ->',a.out)
    for k in sorted(depth_rows): print(k,depth_rows[k],rate_rows[k],counts[k])
if __name__=='__main__': main()
