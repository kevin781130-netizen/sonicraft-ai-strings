#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import mido

TPB=480
BPM=60.0
TEMPO=mido.bpm2tempo(BPM)

def sec_to_ticks(sec: float) -> int:
    return int(round(mido.second2tick(float(sec),TPB,TEMPO)))

def main():
    ap=argparse.ArgumentParser(description="Pack the DNNI capture plan into four long MIDI files so only four long WAV bounces are needed.")
    ap.add_argument("--plan",default="datasets/dnni_four_timbres/capture_plan.jsonl")
    ap.add_argument("--out",default="datasets/dnni_four_timbres/batch_capture")
    ap.add_argument("--lead-sec",type=float,default=1.0)
    ap.add_argument("--gap-sec",type=float,default=0.75)
    ap.add_argument("--lyric",default="la")
    a=ap.parse_args()
    rows=[json.loads(x) for x in Path(a.plan).read_text(encoding="utf-8").splitlines() if x.strip()]
    groups={}
    for r in rows: groups.setdefault(str(r["timbre_id"]),[]).append(r)
    if len(groups)!=4: raise SystemExit(f"expected four timbre groups, got {len(groups)}")
    root=Path(a.out);root.mkdir(parents=True,exist_ok=True)
    mapping={"schema":"sonicraft-dnni-batch-capture-v1","bpm":BPM,"ticks_per_beat":TPB,
             "lead_sec":a.lead_sec,"gap_sec":a.gap_sec,"timbres":[]}
    for tid,items in sorted(groups.items()):
        mid=mido.MidiFile(ticks_per_beat=TPB);track=mido.MidiTrack();mid.tracks.append(track)
        track.append(mido.MetaMessage("track_name",name=tid,time=0))
        track.append(mido.MetaMessage("set_tempo",tempo=TEMPO,time=0))
        current=0.0; outrows=[]
        for i,r in enumerate(items):
            delay=a.lead_sec if i==0 else a.gap_sec
            track.append(mido.MetaMessage("lyrics",text=a.lyric,time=sec_to_ticks(delay)))
            vel=max(1,min(127,int(round(float(r.get("velocity",.7))*127))))
            pitch=max(0,min(127,int(round(float(r["pitch"])))))
            duration=float(r.get("seconds",2.0))
            track.append(mido.Message("note_on",note=pitch,velocity=vel,time=0))
            track.append(mido.Message("note_off",note=pitch,velocity=0,time=sec_to_ticks(duration)))
            current += delay
            rr=dict(r);rr["batch_start_sec"]=round(current,6);rr["batch_end_sec"]=round(current+duration,6)
            rr["midi_velocity"]=vel;outrows.append(rr)
            current += duration
        midi_path=root/f"{tid}.mid";mid.save(midi_path)
        mapping["timbres"].append({"timbre_id":tid,"midi":str(midi_path).replace("\\","/"),
                                   "expected_bounce":f"datasets/dnni_four_timbres/batch_bounces/{tid}.wav",
                                   "duration_sec":round(current+a.gap_sec,3),"captures":outrows})
        print(tid,":",len(items),"captures ->",midi_path,"timeline",round(current,1),"sec")
    mp=root/"batch_capture_map.json"
    mp.write_text(json.dumps(mapping,indent=2,ensure_ascii=False),encoding="utf-8")
    print("Map ->",mp)
    print("Import each MIDI into Synthesizer V Studio 2, assign the matching voice/timbre, then Bounce one WAV per timbre.")

if __name__=="__main__":
    main()
