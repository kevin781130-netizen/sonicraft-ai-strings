#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import mido

TPB=480
BPM=60.0
TEMPO=mido.bpm2tempo(BPM)
NOTES=[28,31,36,40,43,48,52,55,60,64,67,72,76,79,84,88,91,96,100]

def sec_to_ticks(sec: float) -> int:
    return int(round(mido.second2tick(float(sec),TPB,TEMPO)))

def main():
    ap=argparse.ArgumentParser(description="Generate four identical cross-range MIDI probes for DNNI instrument identification.")
    ap.add_argument("--config",default="training/configs/dnni_four_timbres.json")
    ap.add_argument("--out",default="datasets/dnni_four_timbres/identify")
    ap.add_argument("--note-sec",type=float,default=.80)
    ap.add_argument("--gap-sec",type=float,default=.30)
    ap.add_argument("--lead-sec",type=float,default=.75)
    ap.add_argument("--velocity",type=float,default=.72)
    a=ap.parse_args()
    cfg=json.loads(Path(a.config).read_text(encoding="utf-8"))
    slots=sorted(cfg.get("slots",[]),key=lambda x:int(x.get("slot",0)))
    if len(slots)!=4: raise SystemExit("expected exactly four timbre slots")
    root=Path(a.out);root.mkdir(parents=True,exist_ok=True)
    timeline=[]
    t=a.lead_sec
    for i,n in enumerate(NOTES):
        timeline.append({"note":n,"start_sec":round(t,6),"end_sec":round(t+a.note_sec,6)})
        t += a.note_sec + a.gap_sec
    for slot in slots:
        tid=str(slot["timbre_id"])
        mid=mido.MidiFile(ticks_per_beat=TPB);tr=mido.MidiTrack();mid.tracks.append(tr)
        tr.append(mido.MetaMessage("track_name",name=f"{tid}_identify",time=0))
        tr.append(mido.MetaMessage("set_tempo",tempo=TEMPO,time=0))
        vel=max(1,min(127,int(round(a.velocity*127))))
        for i,n in enumerate(NOTES):
            delay=a.lead_sec if i==0 else a.gap_sec
            tr.append(mido.MetaMessage("lyrics",text="la",time=sec_to_ticks(delay)))
            tr.append(mido.Message("note_on",note=n,velocity=vel,time=0))
            tr.append(mido.Message("note_off",note=n,velocity=0,time=sec_to_ticks(a.note_sec)))
        p=root/f"{tid}_identify.mid";mid.save(p)
        print(tid,"->",p)
    manifest={
        "schema":"sonicraft-dnni-identification-probe-v1",
        "bpm":BPM,"lead_sec":a.lead_sec,"note_sec":a.note_sec,"gap_sec":a.gap_sec,
        "velocity":a.velocity,"notes":timeline,
        "slots":[{"slot":int(x["slot"]),"timbre_id":str(x["timbre_id"]),
                  "midi":f"{x['timbre_id']}_identify.mid",
                  "expected_wav":f"bounces/{x['timbre_id']}.wav"} for x in slots],
    }
    (root/"probe_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    print("Bounce one WAV per timbre to",root/"bounces")

if __name__=="__main__":main()
