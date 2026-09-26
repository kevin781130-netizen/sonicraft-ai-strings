#!/usr/bin/env python3
from __future__ import annotations
import json, math, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf

ROOT=Path(__file__).resolve().parents[2]
PY=sys.executable
PROFILES={
    "timbre_1":(55,100),   # violin
    "timbre_2":(36,81),    # cello
    "timbre_3":(28,67),    # double bass
    "timbre_4":(48,88),    # viola
}
EXPECTED={
    "timbre_1":"violin",
    "timbre_2":"cello",
    "timbre_3":"double_bass",
    "timbre_4":"viola",
}

def run(*args):
    subprocess.run([PY,*map(str,args)],cwd=ROOT,check=True)

def main():
    with tempfile.TemporaryDirectory(prefix="dnni_identify_smoke_") as td:
        root=Path(td)
        cfg=root/"cfg.json"
        cfg.write_text(json.dumps({
            "schema":"test",
            "slots":[
                {"slot":1,"timbre_id":"timbre_1","label":"T1","instrument":0,"midi_low":28,"midi_high":100},
                {"slot":2,"timbre_id":"timbre_2","label":"T2","instrument":1,"midi_low":28,"midi_high":100},
                {"slot":3,"timb_id_unused":"x","timbre_id":"timbre_3","label":"T3","instrument":2,"midi_low":28,"midi_high":100},
                {"slot":4,"timbre_id":"timbre_4","label":"T4","instrument":3,"midi_low":28,"midi_high":100},
            ]},indent=2),encoding="utf-8")
        run("training/scripts/generate_dnni_identification_probe.py","--config",cfg,"--out",root)
        probe=json.loads((root/"probe_manifest.json").read_text(encoding="utf-8"))
        sr=12000
        (root/"bounces").mkdir()
        for slot in probe["slots"]:
            tid=slot["timbre_id"];lo,hi=PROFILES[tid]
            dur=probe["notes"][-1]["end_sec"]+.5
            y=np.zeros(int(math.ceil(dur*sr)),np.float32)
            for row in probe["notes"]:
                note=int(row["note"]);st=int(row["start_sec"]*sr);en=int(row["end_sec"]*sr)
                if lo<=note<=hi:
                    t=np.arange(en-st,dtype=np.float32)/sr
                    f=440.0*2**((note-69)/12)
                    sig=.18*np.sin(2*np.pi*f*t)+.07*np.sin(2*np.pi*2*f*t)+.035*np.sin(2*np.pi*3*f*t)
                    y[st:en]=sig.astype(np.float32)
            sf.write(root/"bounces"/f"{tid}.wav",y,sr)
        run("training/scripts/identify_dnni_instruments.py","--root",root,"--config",cfg,"--apply-config","--min-confidence","0.50")
        rep=json.loads((root/"identification_report.json").read_text(encoding="utf-8"))
        got={k:v["instrument_role"] for k,v in rep["labels"].items()}
        assert got==EXPECTED,(got,EXPECTED)
        out=json.loads(cfg.read_text(encoding="utf-8"))
        roles={x["timbre_id"]:x.get("instrument_role") for x in out["slots"]}
        assert roles==EXPECTED,roles
        print("DNNI identification smoke PASS",got)

if __name__=="__main__":main()
