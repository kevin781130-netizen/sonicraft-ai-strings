#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import soundfile as sf

def mono(x):
    if x.ndim==1:return x.astype(np.float32,copy=False)
    return x.mean(axis=1,dtype=np.float32)

def detect_onset(x,sr,search_end):
    y=np.abs(mono(x))
    hop=max(1,int(sr*.01)); n=max(1,int(sr*.02))
    limit=min(len(y),int(search_end*sr))
    if limit<=n:return 0.0
    vals=[]; poss=[]
    for st in range(0,limit-n+1,hop):
        vals.append(float(np.sqrt(np.mean(y[st:st+n]**2)+1e-12)));poss.append(st)
    a=np.asarray(vals,np.float32)
    peak=float(a.max()) if len(a) else 0.0
    noise=float(np.percentile(a[:max(1,min(len(a),50))],30)) if len(a) else 0.0
    thr=max(noise*5.0,peak*.06,1e-5)
    idx=np.flatnonzero(a>=thr)
    return (poss[int(idx[0])]/sr) if len(idx) else 0.0

def main():
    ap=argparse.ArgumentParser(description="Slice four long SynthV batch bounces into the per-capture WAV layout used by SONICRAFT.")
    ap.add_argument("--map",default="datasets/dnni_four_timbres/batch_capture/batch_capture_map.json")
    ap.add_argument("--root",default="datasets/dnni_four_timbres")
    ap.add_argument("--bounces",default="datasets/dnni_four_timbres/batch_bounces")
    ap.add_argument("--prepad-ms",type=float,default=40.0)
    a=ap.parse_args()
    mp=json.loads(Path(a.map).read_text(encoding="utf-8"));root=Path(a.root);broot=Path(a.bounces)
    report={"schema":"sonicraft-dnni-batch-slice-report-v1","timbres":[]}
    total=0
    for group in mp["timbres"]:
        tid=group["timbre_id"];src=broot/f"{tid}.wav"
        if not src.exists(): raise SystemExit(f"missing long bounce: {src}")
        audio,sr=sf.read(src,dtype="float32",always_2d=True)
        caps=group["captures"]
        if not caps: continue
        expected=float(caps[0]["batch_start_sec"])
        onset=detect_onset(audio,sr,expected+3.0)
        offset=onset-expected
        # Keep a small amount of pre-onset room; encoder later crops/pads deterministically.
        pre=max(0.0,float(a.prepad_ms)/1000.0)
        made=0
        for r in caps:
            dur=float(r.get("seconds",2.0))
            start=float(r["batch_start_sec"])+offset-pre
            st=max(0,int(round(start*sr))); en=st+int(round(dur*sr))
            clip=audio[st:min(en,len(audio))]
            if len(clip)<en-st:
                clip=np.pad(clip,((0,en-st-len(clip)),(0,0)))
            out=root/r["expected_wav"];out.parent.mkdir(parents=True,exist_ok=True)
            sf.write(out,clip,sr,subtype="PCM_24")
            made+=1;total+=1
        report["timbres"].append({"timbre_id":tid,"source":str(src),"sample_rate":sr,
                                  "detected_first_onset_sec":round(onset,6),"timeline_offset_sec":round(offset,6),
                                  "captures_written":made})
        print(tid,":",made,"clips","offset",round(offset,4),"sec")
    rp=root/"batch_capture/slice_report.json";rp.parent.mkdir(parents=True,exist_ok=True)
    rp.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("Wrote",total,"capture WAV files; report ->",rp)

if __name__=="__main__":
    main()
