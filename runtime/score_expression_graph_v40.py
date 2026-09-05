"""SONICRAFT v4.0 strings-only Score & Expression Graph.

Dependency-free MusicXML/MXL parser. The graph keeps notation semantics even when the current
acoustic core cannot honestly render a technique; unsupported techniques become warnings instead
of being silently mapped to a fake articulation.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict,field
from pathlib import Path
import zipfile,xml.etree.ElementTree as ET,re,json

PPQ=960
PARTS=("Vln I","Vln II","Viola","Cello")
ART_NAMES=("Sustain","Legato","Portamento","Expressive Long","Marcato","Staccato","Spiccato","Tremolo","Pizzicato","Trill","Harmonic","Flautando")
DYN={"ppp":25,"pp":38,"p":50,"mp":64,"mf":80,"f":96,"ff":110,"fff":122}
STEP={"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}
STACK_BITS={"accent":1,"legato":2,"tenuto":4,"expressive":8}

@dataclass
class ScoreNote:
    part:int;start_tick:int;end_tick:int;pitch:int;velocity:int=82;voice:int=1;staff:int=1
    base_art:int=0;stack:int=0;cc1:int=80;cc3:int=64;tie_start:bool=False;tie_stop:bool=False
    slur:bool=False;technical:list[str]=field(default_factory=list);source_id:str=""
    lane_channel:int=-1
    string_index:int=-1;string_name:str="";finger_semitone:int=-1;position_index:int=0;shift_semitones:int=0
    bow_direction:int=-1;bow_change:bool=False;bow_pressure:float=.5;contact_point:float=.5
    portamento_route:float=0.;divisi_desk:int=0;open_string:bool=False
    physical_warnings:list[str]=field(default_factory=list)
    constraint_flags:list[str]=field(default_factory=list)
    transition_risk:float=0.;bow_budget:float=0.;playability_risk:float=0.
    multi_stop_group_id:int=0;multi_stop_feasible:bool=False;divisi_required:bool=False
    ensemble_group_id:int=0;ensemble_phrase_id:int=0;ensemble_role:str=""
    ensemble_attack_offset_ms:float=0.;ensemble_breath_ms:float=0.;ensemble_bow_sync:bool=False
    ensemble_coordination_risk:float=0.;ensemble_coordination_flags:list[str]=field(default_factory=list)
    gesture_profile:str="";gesture_amount:float=0.;gesture_risk:float=0.;gesture_anchors:list[dict]=field(default_factory=list)
    transition_in_link_id:int=0;transition_out_link_id:int=0
    transition_in_mode:str="";transition_out_mode:str=""
    transition_interval_semitones:int=0;transition_duration_ms:float=0.;transition_continuity:float=0.
    transition_phrase_continuous:bool=False;transition_flags:list[str]=field(default_factory=list)
    phrase_longline_id:int=0;phrase_longline_contour:str="";phrase_longline_apex_u:float=0.
    phrase_longline_enabled:bool=False;phrase_bow_reserve:float=1.;phrase_dynamic_momentum:float=0.
    phrase_vibrato_rate_hz:float=0.;phrase_longline_flags:list[str]=field(default_factory=list)

@dataclass
class ScoreGraph:
    ppq:int=PPQ
    tempos:list[dict]=field(default_factory=list)
    time_signatures:list[dict]=field(default_factory=list)
    key_signatures:list[dict]=field(default_factory=list)
    notes:list[ScoreNote]=field(default_factory=list)
    warnings:list[dict]=field(default_factory=list)

def _strip(tag):return tag.rsplit('}',1)[-1]
def _child(el,name):
    for x in el:
        if _strip(x.tag)==name:return x
    return None
def _children(el,name):return [x for x in el if _strip(x.tag)==name]
def _text(el,name,default=None):
    x=_child(el,name)
    return (x.text.strip() if x is not None and x.text else default)

def _xml_root(path:Path):
    if path.suffix.lower()==".mxl":
        with zipfile.ZipFile(path) as z:
            name=None
            try:
                c=ET.fromstring(z.read("META-INF/container.xml"))
                for e in c.iter():
                    if _strip(e.tag)=="rootfile":name=e.attrib.get("full-path");break
            except Exception:pass
            if not name:
                name=next(n for n in z.namelist() if n.lower().endswith((".xml",".musicxml")) and not n.startswith("META-INF/"))
            return ET.fromstring(z.read(name))
    return ET.parse(path).getroot()

def _part_index(name:str,order:int):
    s=re.sub(r"[^a-z0-9]+"," ",(name or "").lower())
    if "viola" in s:return 2
    if "cello" in s or "violoncello" in s:return 3
    if "violin" in s:
        if re.search(r"\b(2|ii|second)\b",s):return 1
        return 0
    return order if 0<=order<4 else -1

def _midi_pitch(note):
    pitch=_child(note,"pitch")
    if pitch is None:return None
    step=_text(pitch,"step","C");octv=int(_text(pitch,"octave","4"));alter=int(float(_text(pitch,"alter","0")))
    return max(0,min(127,12*(octv+1)+STEP.get(step,0)+alter))

def _parse_notation(note):
    base=0;stack=0;tech=[];slur=False
    nots=_child(note,"notations")
    if nots is None:return base,stack,tech,slur
    for e in nots.iter():
        tag=_strip(e.tag)
        if tag=="staccato":base=5
        elif tag=="staccatissimo":base=6
        elif tag in ("accent","strong-accent"):stack|=STACK_BITS["accent"]
        elif tag=="tenuto":stack|=STACK_BITS["tenuto"]
        elif tag=="slur":
            slur=True;stack|=STACK_BITS["legato"]
        elif tag=="tremolo":base=7
        elif tag=="trill-mark":base=9
        elif tag=="harmonic":base=10
        elif tag in ("glissando","slide"):base=2
        elif tag in ("up-bow","down-bow","open-string","snap-pizzicato","stopped"):
            tech.append(tag)
    if slur and base==0:base=1
    return base,stack,tech,slur

def parse_score(path:Path)->ScoreGraph:
    root=_xml_root(path);g=ScoreGraph()
    part_names={}
    plist=next((e for e in root if _strip(e.tag)=="part-list"),None)
    if plist is not None:
        for sp in plist:
            if _strip(sp.tag)!="score-part":continue
            part_names[sp.attrib.get("id","")]=_text(sp,"part-name","")
    part_order=0
    for part in [e for e in root if _strip(e.tag)=="part"]:
        pid=part.attrib.get("id","");pidx=_part_index(part_names.get(pid,""),part_order);part_order+=1
        if pidx<0:
            g.warnings.append({"type":"ignored_non_string_part","part":part_names.get(pid,pid)});continue
        divisions=1;cursor=0;last_note_start=0;current_dyn=80;wedge=None;technique_mode=None;expressive_mode=False
        for measure in _children(part,"measure"):
            attrs=_child(measure,"attributes")
            if attrs is not None:
                d=_text(attrs,"divisions")
                if d:divisions=max(1,int(float(d)))
                time=_child(attrs,"time")
                if time is not None:
                    g.time_signatures.append({"tick":cursor,"numerator":int(_text(time,"beats","4")),"denominator":int(_text(time,"beat-type","4"))})
                key=_child(attrs,"key")
                if key is not None:g.key_signatures.append({"tick":cursor,"fifths":int(_text(key,"fifths","0"))})
            for item in measure:
                tag=_strip(item.tag)
                if tag=="direction":
                    sound=_child(item,"sound")
                    if sound is not None and sound.attrib.get("tempo"):
                        g.tempos.append({"tick":cursor,"bpm":float(sound.attrib["tempo"])})
                    if sound is not None and "pizzicato" in sound.attrib:
                        technique_mode="pizzicato" if sound.attrib.get("pizzicato","").lower() in ("yes","true","1") else None
                    for e in item.iter():
                        et=_strip(e.tag)
                        if et=="dynamics":
                            for d in list(e):
                                if _strip(d.tag) in DYN:current_dyn=DYN[_strip(d.tag)]
                        elif et=="wedge":
                            typ=e.attrib.get("type","")
                            if typ in ("crescendo","diminuendo"):wedge=typ
                            elif typ=="stop":wedge=None
                        elif et=="words" and e.text:
                            words=e.text.strip().lower()
                            if "espress" in words or "dolce" in words:
                                expressive_mode=True;current_dyn=min(127,current_dyn+2)
                            if "pizz" in words: technique_mode="pizzicato"
                            if "flautando" in words: technique_mode="flautando"
                            if "arco" in words: technique_mode=None
                            if "ordinario" in words or "normale" in words:
                                technique_mode=None;expressive_mode=False
                            if any(x in words for x in ("col legno","sul ponticello","sul tasto")):
                                technique_mode=words
                                g.warnings.append({"type":"unsupported_string_technique","part":PARTS[pidx],"tick":cursor,"technique":words})
                elif tag=="backup":
                    cursor-=int(round(float(_text(item,"duration","0"))/divisions*PPQ))
                elif tag=="forward":
                    cursor+=int(round(float(_text(item,"duration","0"))/divisions*PPQ))
                elif tag=="note":
                    if _child(item,"rest") is not None:
                        if _child(item,"chord") is None:cursor+=int(round(float(_text(item,"duration","0"))/divisions*PPQ))
                        continue
                    dur=max(1,int(round(float(_text(item,"duration","0"))/divisions*PPQ)))
                    chord=_child(item,"chord") is not None
                    start=last_note_start if chord else cursor
                    if not chord:last_note_start=start
                    pitch=_midi_pitch(item)
                    if pitch is None:continue
                    base,stack,tech,slur=_parse_notation(item)
                    if expressive_mode: stack|=STACK_BITS["expressive"]
                    if technique_mode=="pizzicato" and base==0: base=8
                    elif technique_mode=="flautando" and base==0: base=11
                    elif technique_mode and technique_mode not in ("pizzicato","flautando"):
                        tech.append(technique_mode)
                    # MusicXML pizzicato is often a sound attribute.
                    for e in item.iter():
                        if _strip(e.tag)=="technical":
                            for x in e:
                                xt=_strip(x.tag)
                                if xt in ("harmonic","up-bow","down-bow","open-string","snap-pizzicato"):tech.append(xt)
                    tie_start=any(_strip(x.tag)=="tie" and x.attrib.get("type")=="start" for x in item)
                    tie_stop=any(_strip(x.tag)=="tie" and x.attrib.get("type")=="stop" for x in item)
                    if any("snap-pizzicato"==x for x in tech):base=8
                    # Wedges influence note-level CC1 conservatively; original direction remains in graph timing.
                    cc1=current_dyn+(6 if wedge=="crescendo" else (-6 if wedge=="diminuendo" else 0))
                    if stack&STACK_BITS["accent"]:cc1+=4
                    cc1=max(1,min(127,cc1))
                    cc3=max(0,min(127,42+(18 if dur>PPQ else 0)+(12 if stack&STACK_BITS["expressive"] else 0)))
                    n=ScoreNote(pidx,start,start+dur,pitch,max(1,min(127,int(_text(item,"velocity","82")))),
                                int(_text(item,"voice","1")),int(_text(item,"staff","1")),base,stack,cc1,cc3,tie_start,tie_stop,slur,tech,
                                f"{pid}:{measure.attrib.get('number','')}:{len(g.notes)}")
                    g.notes.append(n)
                    if not chord:cursor+=dur
    if not g.tempos:g.tempos=[{"tick":0,"bpm":120.0}]
    if not g.time_signatures:g.time_signatures=[{"tick":0,"numerator":4,"denominator":4}]
    if not g.key_signatures:g.key_signatures=[{"tick":0,"fifths":0}]
    g.tempos=sorted({(x["tick"],x["bpm"]):(x) for x in g.tempos}.values(),key=lambda x:x["tick"])
    g.time_signatures=sorted({(x["tick"],x["numerator"],x["denominator"]):x for x in g.time_signatures}.values(),key=lambda x:x["tick"])
    g.key_signatures=sorted({(x["tick"],x["fifths"]):x for x in g.key_signatures}.values(),key=lambda x:x["tick"])
    _merge_ties(g)
    return g

def _merge_ties(g:ScoreGraph):
    out=[];active={}
    for n in sorted(g.notes,key=lambda x:(x.part,x.start_tick,x.voice,x.staff,x.pitch)):
        key=(n.part,n.voice,n.staff,n.pitch)
        if n.tie_stop and key in active:
            prev=active[key];prev.end_tick=max(prev.end_tick,n.end_tick);prev.tie_start=n.tie_start
            prev.stack|=n.stack;prev.slur=prev.slur or n.slur;prev.technical += [x for x in n.technical if x not in prev.technical]
            if not n.tie_start:active.pop(key,None)
            continue
        out.append(n)
        if n.tie_start:active[key]=n
    g.notes=sorted(out,key=lambda x:(x.start_tick,x.part,x.pitch))

def graph_dict(g:ScoreGraph):
    return {"schema":10,"ppq":g.ppq,"parts":list(PARTS),"articulations":list(ART_NAMES),
            "expression_modifiers":STACK_BITS,"tempos":g.tempos,"time_signatures":g.time_signatures,
            "key_signatures":g.key_signatures,"notes":[asdict(n) for n in g.notes],"warnings":g.warnings}
