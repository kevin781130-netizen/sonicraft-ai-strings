#!/usr/bin/env python3
from __future__ import annotations
import argparse, itertools, json, math
from pathlib import Path
import numpy as np
import soundfile as sf

PROFILES={
    "violin":{"label":"Violin","low":55,"high":100},
    "viola":{"label":"Viola","low":48,"high":88},
    "cello":{"label":"Cello","low":36,"high":81},
    "double_bass":{"label":"Double Bass","low":28,"high":67},
}

def rms(x):
    if len(x)==0:return 0.0
    return float(np.sqrt(np.mean(np.square(x,dtype=np.float64))+1e-12))

def mono(x):
    if x.ndim==1:return x.astype(np.float32,copy=False)
    return x.mean(axis=1,dtype=np.float32)

def harmonic_score(x,sr,note):
    x=mono(x)
    if len(x)<64:return 0.0
    x=x-np.mean(x)
    w=np.hanning(len(x)).astype(np.float32)
    spec=np.abs(np.fft.rfft(x*w))
    power=spec*spec
    total=float(power.sum()+1e-12)
    f0=440.0*(2.0**((float(note)-69.0)/12.0))
    freqs=np.fft.rfftfreq(len(x),1.0/sr)
    e=0.0
    for h in range(1,7):
        f=f0*h
        if f>=sr/2:break
        bw=max(12.0,f*.025)
        mask=(freqs>=f-bw)&(freqs<=f+bw)
        if np.any(mask): e+=float(power[mask].sum())
    return min(1.0,e/total)

def detect_global_offset(y,sr,expected_first,search_extra=2.0):
    a=np.abs(mono(y))
    hop=max(1,int(sr*.01));win=max(1,int(sr*.04))
    lim=min(len(a),int((expected_first+search_extra)*sr))
    vals=[];poss=[]
    for st in range(0,max(1,lim-win+1),hop):
        vals.append(rms(a[st:st+win]));poss.append(st)
    if not vals:return 0.0
    v=np.asarray(vals)
    base=float(np.percentile(v[:max(1,min(len(v),40))],30))
    peak=float(v.max())
    thr=max(base*5.0,peak*.08,1e-5)
    ids=np.flatnonzero(v>=thr)
    onset=(poss[int(ids[0])]/sr) if len(ids) else expected_first
    return onset-expected_first

def analyze_one(path,probe):
    audio,sr=sf.read(path,dtype="float32",always_2d=True)
    y=mono(audio)
    notes=probe["notes"]
    off=detect_global_offset(y,sr,float(notes[0]["start_sec"]))
    raw=[]
    for row in notes:
        st=float(row["start_sec"])+off
        en=float(row["end_sec"])+off
        # central 70% avoids attacks/releases dominating the range test.
        dur=max(.05,en-st);a=st+dur*.15;b=en-dur*.15
        i=max(0,int(a*sr));j=min(len(y),int(b*sr))
        clip=y[i:j]
        raw.append({"note":int(row["note"]),"rms":rms(clip),"harmonic":harmonic_score(clip,sr,int(row["note"]))})
    mx=max((x["rms"] for x in raw),default=1e-9)
    for x in raw:
        x["rel_rms"]=x["rms"]/max(mx,1e-9)
        x["voice_score"]=x["rel_rms"]*(0.35+0.65*x["harmonic"])
        x["active"]=bool(x["rel_rms"]>=.12 and x["harmonic"]>=.035)
    act=[x["note"] for x in raw if x["active"]]
    return {"wav":str(path),"sample_rate":sr,"timeline_offset_sec":round(off,5),
            "observed_low":min(act) if act else None,"observed_high":max(act) if act else None,
            "notes":raw}

def profile_cost(obs,profile):
    rows=obs["notes"]
    # Prefer agreement with playable-region response; tolerate occasional extrapolated notes.
    mask_cost=0.0;weight=0.0
    for r in rows:
        expected=profile["low"]<=r["note"]<=profile["high"]
        s=float(r["voice_score"])
        w=1.0
        mask_cost += (1.0-s if expected else s*.72)*w
        weight += w
    mask_cost/=max(weight,1.0)
    lo=obs["observed_low"];hi=obs["observed_high"]
    range_cost=0.0
    if lo is not None: range_cost += min(1.5,abs(lo-profile["low"])/18.0)
    else: range_cost += 1.5
    if hi is not None: range_cost += min(1.5,abs(hi-profile["high"])/24.0)
    else: range_cost += 1.5
    return mask_cost + .38*range_cost

def assign(observations):
    tids=list(observations)
    roles=list(PROFILES)
    scored=[]
    for perm in itertools.permutations(roles):
        total=sum(profile_cost(observations[tid],PROFILES[role]) for tid,role in zip(tids,perm))
        scored.append((total,perm))
    scored.sort(key=lambda x:x[0])
    best,second=scored[0],scored[1]
    overall_gap=max(0.0,second[0]-best[0])
    out={}
    for tid,role in zip(tids,best[1]):
        costs=sorted((profile_cost(observations[tid],p),name) for name,p in PROFILES.items())
        own=next(x for x in costs if x[1]==role)[0]
        alt=min(x[0] for x in costs if x[1]!=role)
        margin=max(0.0,alt-own)
        conf=max(0.05,min(.99,.45+.30*margin+.20*overall_gap))
        out[tid]={"instrument_role":role,"label":PROFILES[role]["label"],
                  "confidence":round(conf,3),"cost":round(own,4),
                  "observed_low":observations[tid]["observed_low"],
                  "observed_high":observations[tid]["observed_high"]}
    return out,{"best_total_cost":round(best[0],4),"second_total_cost":round(second[0],4),"assignment_gap":round(overall_gap,4)}

def apply_config(path,labels):
    cfg=json.loads(Path(path).read_text(encoding="utf-8"))
    for slot in cfg.get("slots",[]):
        tid=str(slot.get("timbre_id"))
        if tid in labels:
            x=labels[tid]
            slot["label"]=x["label"]
            slot["instrument_role"]=x["instrument_role"]
            slot["identification_confidence"]=x["confidence"]
            slot["identification_method"]="acoustic_range_probe_v1"
    Path(path).write_text(json.dumps(cfg,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default="datasets/dnni_four_timbres/identify")
    ap.add_argument("--config",default="training/configs/dnni_four_timbres.json")
    ap.add_argument("--apply-config",action="store_true")
    ap.add_argument("--min-confidence",type=float,default=.58)
    a=ap.parse_args()
    root=Path(a.root);probe=json.loads((root/"probe_manifest.json").read_text(encoding="utf-8"))
    observations={}
    for slot in probe["slots"]:
        tid=str(slot["timbre_id"]);wav=root/slot["expected_wav"]
        if not wav.exists(): raise SystemExit(f"missing identification bounce: {wav}")
        observations[tid]=analyze_one(wav,probe)
    labels,summary=assign(observations)
    confident=all(x["confidence"]>=a.min_confidence for x in labels.values())
    report={"schema":"sonicraft-dnni-instrument-identification-v1",
            "method":"cross_range_rms_harmonic_global_assignment",
            "profiles":PROFILES,"summary":summary,"confident":confident,
            "labels":labels,"observations":observations}
    out=root/"identification_report.json";out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    for tid,x in labels.items():
        print(f"{tid:12s} -> {x['label']:12s} confidence={x['confidence']:.3f} observed={x['observed_low']}..{x['observed_high']}")
    print("report ->",out)
    if a.apply_config:
        if not confident:
            raise SystemExit(f"not applying config: at least one confidence is below {a.min_confidence:.2f}; inspect the report/listen to probes")
        apply_config(a.config,labels)
        print("labels applied ->",a.config)

if __name__=="__main__":main()
