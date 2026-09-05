"""SONICRAFT v5.1 Selective Phrase Search.

Turns v4.8 structural-critic issues + repair edit locations into a small set of local render windows.
This module is score-domain only; it never decides the sonic winner.

Fallback is deliberately conservative when:
- no reliable problem location exists,
- the selected windows cover too much of the song,
- too many disjoint windows are required,
- issue source IDs cannot be mapped back to the score.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict,field
from collections import defaultdict
from string_performance_critic_v48 import WEIGHTS

PPQ=960

@dataclass
class PhraseWindowV51:
    window_id:int
    start_tick:int
    end_tick:int
    phrase_keys:list[str]=field(default_factory=list)
    source_ids:list[str]=field(default_factory=list)
    dimensions:list[str]=field(default_factory=list)
    priority:float=0.0
    issue_count:int=0

@dataclass
class SelectivePlanV51:
    selective:bool
    fallback_reason:str
    song_start_tick:int
    song_end_tick:int
    coverage:float
    windows:list[PhraseWindowV51]
    mapped_issue_sources:int
    unknown_issue_sources:int
    problem_groups:int
    total_groups:int
    def as_dict(self):
        return {
            "schema":1,"version":"5.1","selective":self.selective,
            "fallback_reason":self.fallback_reason,
            "song_start_tick":self.song_start_tick,"song_end_tick":self.song_end_tick,
            "coverage":round(float(self.coverage),6),
            "mapped_issue_sources":self.mapped_issue_sources,
            "unknown_issue_sources":self.unknown_issue_sources,
            "problem_groups":self.problem_groups,"total_groups":self.total_groups,
            "windows":[asdict(x) for x in self.windows],
        }

def _group_key(n):
    pid=int(getattr(n,"phrase_longline_id",0) or 0)
    return f"phrase:{pid}" if pid else f"note:{n.source_id}"

def _group_notes(g):
    by=defaultdict(list)
    for n in g.notes:
        by[_group_key(n)].append(n)
    for ns in by.values():
        ns.sort(key=lambda n:(int(n.start_tick),int(n.end_tick),int(n.pitch)))
    return dict(by)

def _severity_weight(sev):
    return {"error":3.0,"warning":2.0,"info":1.0}.get(str(sev).lower(),1.0)

def _dimension_weight(dim):
    return 1.0+2.0*float(WEIGHTS.get(str(dim),.10))

def _latent_risk(n):
    p=0.0
    reserve=float(getattr(n,"phrase_bow_reserve",1.0))
    if reserve<.18:p+=(.18-reserve)*8.0+.25
    tr=float(getattr(n,"transition_risk",0.0))
    if tr>.52:p+=(tr-.52)*2.4
    er=float(getattr(n,"ensemble_coordination_risk",0.0))
    if er>.22:p+=(er-.22)*1.4
    gr=float(getattr(n,"gesture_risk",0.0))
    if gr>.35:p+=(gr-.35)*1.2
    return p

def build_selective_plan_v51(g,issues,reports=None,max_windows=6,coverage_limit=.55,
                             problem_floor=.65,merge_gap_ticks=PPQ//3):
    reports=reports or {}
    notes=list(g.notes)
    if not notes:
        return SelectivePlanV51(False,"empty_score",0,0,1.0,[],0,0,0,0)

    groups=_group_notes(g)
    source_to_group={}
    for key,ns in groups.items():
        for n in ns:source_to_group[str(n.source_id)]=key

    score=defaultdict(float)
    dims=defaultdict(set)
    sources=defaultdict(set)
    issue_counts=defaultdict(int)
    mapped=0;unknown=0

    for issue in issues or []:
        dim=str(getattr(issue,"dimension","unknown"))
        sev=_severity_weight(getattr(issue,"severity","warning"))
        srcs=list(getattr(issue,"source_ids",[]) or [])
        if not srcs:
            # Global issue: add a small amount to all groups rather than fabricating a location.
            for key in groups:
                score[key]+=sev*.15*_dimension_weight(dim);dims[key].add(dim)
            continue
        for sid in srcs:
            key=source_to_group.get(str(sid))
            if key is None:
                unknown+=1;continue
            mapped+=1
            score[key]+=sev*_dimension_weight(dim)
            dims[key].add(dim);sources[key].add(str(sid));issue_counts[key]+=1

    # Repair reports reveal where A/B/C actually intend to edit. Add low weight so they cannot
    # override a real critic issue, but they prevent silently ignoring an edited phrase.
    for slot,rep in (reports or {}).items():
        for edit in getattr(rep,"edits",[]) or []:
            touched=set()
            for sid in edit.get("source_ids",[]) or []:
                key=source_to_group.get(str(sid))
                if key:touched.add(key);sources[key].add(str(sid))
            pid=edit.get("phrase_id")
            if pid is not None and f"phrase:{int(pid)}" in groups:
                touched.add(f"phrase:{int(pid)}")
            tick=edit.get("tick")
            if tick is not None:
                tt=int(tick)
                for key,ns in groups.items():
                    if min(n.start_tick for n in ns)<=tt<=max(n.end_tick for n in ns):
                        touched.add(key)
            for key in touched:
                score[key]+=.15
                dims[key].add(f"repair_{str(slot)}")

    # Latent risk covers issue source-id truncation and notes that crossed a threshold after
    # a previous planner pass.
    for key,ns in groups.items():
        latent=sum(_latent_risk(n) for n in ns)/max(1,len(ns))
        if latent>0:
            score[key]+=latent
            dims[key].add("latent_playability")

    candidates=[]
    for key,ns in groups.items():
        pr=float(score.get(key,0.0))
        if pr<problem_floor:continue
        candidates.append({
            "key":key,
            "start":min(int(n.start_tick) for n in ns),
            "end":max(int(n.end_tick) for n in ns),
            "priority":pr,
            "sources":sorted(sources.get(key,set()) or {str(n.source_id) for n in ns}),
            "dims":sorted(dims.get(key,set())),
            "issues":int(issue_counts.get(key,0)),
        })

    song_start=min(int(n.start_tick) for n in notes)
    song_end=max(int(n.end_tick) for n in notes)
    span=max(1,song_end-song_start)

    if not candidates:
        return SelectivePlanV51(False,"no_localized_problem",song_start,song_end,1.0,[],
                                mapped,unknown,0,len(groups))

    # Merge time-overlapping problem groups across string sections. Local Shadow Render is an
    # ensemble render, so simultaneous Vln I / Viola issues should be judged together.
    candidates.sort(key=lambda x:(x["start"],x["end"]))
    merged=[]
    for c in candidates:
        if not merged or c["start"]>merged[-1]["end"]+int(merge_gap_ticks):
            merged.append(dict(c,keys=[c["key"]]))
        else:
            m=merged[-1]
            m["end"]=max(m["end"],c["end"])
            m["priority"]+=c["priority"]
            m["sources"]=sorted(set(m["sources"])|set(c["sources"]))
            m["dims"]=sorted(set(m["dims"])|set(c["dims"]))
            m["issues"]+=c["issues"];m["keys"].append(c["key"])

    windows=[]
    for i,m in enumerate(merged,1):
        windows.append(PhraseWindowV51(
            i,m["start"],m["end"],sorted(set(m["keys"])),m["sources"],m["dims"],
            round(float(m["priority"]),6),int(m["issues"])
        ))

    coverage=sum(max(0,w.end_tick-w.start_tick) for w in windows)/float(span)
    issue_total=mapped+unknown
    unknown_ratio=(unknown/issue_total) if issue_total else 0.0
    reason=""
    if len(windows)>int(max_windows):reason="too_many_problem_windows"
    elif coverage>float(coverage_limit):reason="problem_coverage_too_large"
    elif unknown_ratio>.25:reason="critic_location_mapping_incomplete"

    return SelectivePlanV51(not bool(reason),reason,song_start,song_end,coverage,windows,
                            mapped,unknown,len(candidates),len(groups))
