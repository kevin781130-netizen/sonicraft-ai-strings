"""SONICRAFT v4.9 compiled-MIDI -> Audio Judge event adapter.

The existing Audio Judge needs authored note onsets and dynamics intent. Each A/B/C/D render is
judged against its own candidate MIDI, so a repaired dynamic arc is not unfairly scored against D.
"""
from __future__ import annotations
from pathlib import Path
from compile_midi_performance_v29 import parse_midi

def _tempo_points(tracks):
    pts=[(0,500000)] # 120 BPM default
    for tr in tracks:
        for e in tr:
            if e.status==0xFF and e.data and e.data[0]==0x51 and len(e.data)>=4:
                us=(e.data[1]<<16)|(e.data[2]<<8)|e.data[3]
                pts.append((int(e.tick),max(1,us)))
    d={}
    for tick,us in pts:d[tick]=us
    return sorted(d.items())

def _tick_to_seconds_fn(division,tempo):
    seg=[]
    sec=0.0;last_tick=tempo[0][0];us=tempo[0][1]
    if last_tick>0:last_tick=0
    for tick,new_us in tempo[1:]:
        if tick<last_tick:continue
        seg.append((last_tick,tick,sec,us))
        sec+=(tick-last_tick)/float(division)*us/1e6
        last_tick=tick;us=new_us
    seg.append((last_tick,10**18,sec,us))
    def conv(tick):
        tick=int(tick)
        for a,b,s,u in seg:
            if a<=tick<b:return s+(tick-a)/float(division)*u/1e6
        a,b,s,u=seg[-1];return s+(tick-a)/float(division)*u/1e6
    return conv

def midi_to_judge_events_v49(path,sample_rate,end_sample=None):
    fmt,division,tracks=parse_midi(Path(path))
    tempo=_tempo_points(tracks);to_sec=_tick_to_seconds_fn(division,tempo)
    controls={ch:[.62,.50,.50,.50,.50,.50,.50,.0,.50,.50,.50,.50,.38,.0] for ch in range(16)}
    events=[]
    merged=sorted((e for tr in tracks for e in tr),key=lambda e:(e.tick,e.track,e.order))
    for e in merged:
        if e.status>=0xF0:continue
        hi=e.status&0xF0;ch=e.status&0x0F
        ps=int(round(to_sec(e.tick)*sample_rate))
        if end_sample is not None and ps>end_sample:continue
        if hi==0xB0 and len(e.data)>=2:
            cc,val=e.data[0],e.data[1]/127.0
            # Judge only needs authored dynamics in controls[0], but carry a few nearby fields too.
            if cc==22:controls[ch][0]=val
            elif cc==23:controls[ch][1]=val
            elif cc==24:controls[ch][2]=val
            elif cc==25:controls[ch][12]=val
            elif cc==31:controls[ch][8]=val
            elif cc==34:controls[ch][10]=val
            events.append({"project_sample":ps,"type":4,"part":max(0,min(3,e.track-1)),
                           "voice_lane":ch,"note":cc,"velocity":val,"controls":list(controls[ch])})
        elif hi==0x90 and len(e.data)>=2 and e.data[1]>0 and e.data[0]>=12:
            events.append({"project_sample":ps,"type":1,"part":max(0,min(3,e.track-1)),
                           "voice_lane":ch,"note":e.data[0],"velocity":e.data[1]/127.0,
                           "controls":list(controls[ch])})
        elif (hi==0x80 or (hi==0x90 and len(e.data)>=2 and e.data[1]==0)) and len(e.data)>=1 and e.data[0]>=12:
            events.append({"project_sample":ps,"type":2,"part":max(0,min(3,e.track-1)),
                           "voice_lane":ch,"note":e.data[0],"velocity":0.0,
                           "controls":list(controls[ch])})
    return events
