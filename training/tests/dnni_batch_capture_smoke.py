#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf

ROOT=Path(__file__).resolve().parents[2]
PY=sys.executable

def run(*args):
    subprocess.run([PY,*map(str,args)],cwd=ROOT,check=True)

def main():
    with tempfile.TemporaryDirectory(prefix="dnni_batch_smoke_") as td:
        root=Path(td)
        plan=root/"plan.jsonl";batch=root/"batch";bounces=root/"bounces"
        run("training/scripts/generate_dnni_capture_plan.py","--out",plan,
            "--pitches-per-timbre","1","--velocities","0.70","--seconds","0.10")
        run("training/scripts/generate_dnni_batch_capture_midi.py","--plan",plan,"--out",batch,
            "--lead-sec","0.20","--gap-sec","0.10")
        mp=json.loads((batch/"batch_capture_map.json").read_text(encoding="utf-8"))
        assert len(mp["timbres"])==4
        bounces.mkdir(parents=True,exist_ok=True)
        sr=8000
        for g in mp["timbres"]:
            dur=max(.5,float(g["duration_sec"])+.25)
            x=np.zeros(int(round(dur*sr)),np.float32)
            # Put simple audible blocks at each scheduled note. This also tests onset offset handling.
            for r in g["captures"]:
                st=int(round(float(r["batch_start_sec"])*sr))
                en=min(len(x),st+int(round(float(r["seconds"])*sr)))
                x[st:en]=.12
            sf.write(bounces/f"{g['timbre_id']}.wav",x,sr)
        run("training/scripts/slice_dnni_batch_bounces.py","--map",batch/"batch_capture_map.json",
            "--root",root,"--bounces",bounces)
        out=root/"rendered/index.jsonl"
        run("training/scripts/build_dnni_render_manifest.py","--plan",plan,"--root",root,"--out",out)
        rows=[json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
        assert len(rows)==48, len(rows)
        assert all(Path(r["audio"]).exists() for r in rows)
        assert all(r.get("articulation_known")==0.0 for r in rows)
        assert all(r.get("velocity_verified") is False for r in rows)
        print("DNNI batch capture smoke PASS:",len(rows),"clips")

if __name__=="__main__":
    main()
