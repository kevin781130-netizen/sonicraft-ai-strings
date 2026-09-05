"""SONICRAFT v4.3 String Constraint & Transition Solver.

Strings-only score-domain solver. It has full future context, so it belongs before MIDI rendering
rather than inside the real-time audio callback. The solver:
- validates configured instrument/string range,
- repairs high-cost string/fingering transitions when a local feasible alternative exists,
- tracks bow budget across connected phrases and inserts a bow change before exhaustion,
- analyzes simultaneous stops and marks double/multi-stop feasibility vs divisi requirement,
- produces explicit risk/constraint metadata instead of silently forcing impossible writing.

This is an ergonomic rule system, not a claim of biomechanical certainty.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from math import inf
from typing import Iterable

from score_expression_graph_v40 import PARTS, PPQ
from string_physical_graph_v42 import (
    OPEN_STRINGS, STRING_NAMES, feasible_fingerings, plan_bowing, plan_portamento,
)

MAX_PITCH = {0:103, 1:103, 2:96, 3:88}   # conservative configured planning caps
MIN_PITCH = {p:min(OPEN_STRINGS[p]) for p in range(4)}
MAX_STOP_SPAN = {0:7,1:7,2:7,3:8}        # semitone hand-frame heuristic
BOW_BUDGET_BEATS = {0:5.0,1:5.0,2:5.4,3:5.8}

@dataclass
class ConstraintIssue:
    severity:str
    kind:str
    part:int
    tick:int
    source_ids:list[str]=field(default_factory=list)
    detail:str=""

@dataclass
class ConstraintReport:
    issues:list[ConstraintIssue]=field(default_factory=list)
    simultaneous_groups:list[dict]=field(default_factory=list)
    repaired_transitions:int=0
    forced_bow_changes:int=0
    unplayable_notes:int=0
    max_risk:float=0.0

    def as_dict(self):
        return {
            "issues":[asdict(x) for x in self.issues],
            "simultaneous_groups":self.simultaneous_groups,
            "repaired_transitions":self.repaired_transitions,
            "forced_bow_changes":self.forced_bow_changes,
            "unplayable_notes":self.unplayable_notes,
            "max_risk":round(float(self.max_risk),6),
        }

def _tempo_at(g,tick):
    bpm=120.0
    for x in sorted(g.tempos,key=lambda y:int(y["tick"])):
        if int(x["tick"])>tick:break
        bpm=float(x["bpm"])
    return max(24.0,bpm)

def _duration_beats(n):
    return max(1.0/PPQ,(n.end_tick-n.start_tick)/float(PPQ))

def _gap_beats(prev,n):
    return max(0.0,(n.start_tick-prev.end_tick)/float(PPQ))

def _connected(prev,n):
    return n.start_tick-prev.end_tick <= max(40,PPQ//48) and (
        prev.slur or n.slur or (prev.stack&2) or (n.stack&2) or prev.base_art in (1,2) or n.base_art in (1,2)
    )

def _transition_risk(prev,n):
    shift=abs(int(n.finger_semitone)-int(prev.finger_semitone))
    crossing=abs(int(n.string_index)-int(prev.string_index))
    gap=_gap_beats(prev,n)
    bpm=_tempo_at_dummy(n)
    # normalized ergonomic risk; connected shifts are stricter than detached recovery.
    time_relief=min(1.0,gap*1.8)
    base=(shift/12.0)+(crossing*.18)-time_relief*.35
    if _connected(prev,n):base+=max(0,shift-4)*.035+crossing*.07
    return max(0.0,min(1.0,base))

def _tempo_at_dummy(n):
    # retained only to keep transition risk independent of any hidden external state
    return 120.0

def _local_transition_cost(prev,n,cand):
    s,f=cand
    shift=abs(f-int(prev.finger_semitone))
    crossing=abs(s-int(prev.string_index))
    cost=shift*.12+crossing*.42
    if _connected(prev,n):
        cost += max(0,shift-5)*.13 + crossing*.24
    if f==0 and (n.slur or (n.stack&2) or (n.stack&8) or n.base_art in (1,2,3,11)):
        cost+=.85
    if f>20:cost+=(f-20)*.035
    return cost

def _repair_lane(notes,report):
    prev=None
    for n in notes:
        if prev is None:
            prev=n;continue
        current=(int(n.string_index),int(n.finger_semitone))
        current_cost=_local_transition_cost(prev,n,current)
        candidates=feasible_fingerings(n.part,n.pitch)
        if candidates:
            best=min(candidates,key=lambda c:_local_transition_cost(prev,n,c))
            best_cost=_local_transition_cost(prev,n,best)
            # Require a meaningful improvement to avoid gratuitous fingering churn.
            if current_cost-best_cost>.42:
                n.string_index,n.finger_semitone=best
                n.string_name=STRING_NAMES[n.part][best[0]]
                n.position_index=0 if best[1]==0 else max(1,1+(best[1]-1)//4)
                n.open_string=(best[1]==0)
                n.shift_semitones=best[1]-int(prev.finger_semitone)
                n.constraint_flags.append("transition_repaired")
                report.repaired_transitions+=1
        shift=abs(int(n.finger_semitone)-int(prev.finger_semitone))
        crossing=abs(int(n.string_index)-int(prev.string_index))
        risk=max(0.0,min(1.0,shift/12.0+crossing*.18-(min(1.0,_gap_beats(prev,n)*1.8)*.35)))
        if _connected(prev,n):
            risk=max(risk,min(1.0,shift/10.0+crossing*.14))
        n.transition_risk=risk
        report.max_risk=max(report.max_risk,risk)
        if risk>=.72:
            n.constraint_flags.append("high_transition_risk")
            report.issues.append(ConstraintIssue(
                "warning","high_transition_risk",n.part,n.start_tick,[prev.source_id,n.source_id],
                f"shift={shift} semitones, string_crossing={crossing}, risk={risk:.3f}"
            ))
        prev=n

def _bow_budget_lane(notes,report):
    budget=0.0;prev=None
    limit=BOW_BUDGET_BEATS[notes[0].part] if notes else 5.0
    for n in notes:
        if prev is None or _gap_beats(prev,n)>=1.0:
            budget=0.0
        consumption=_duration_beats(n)*(0.52+float(n.bow_pressure)*.62)
        connected=prev is not None and _connected(prev,n)
        if connected and not n.bow_change and budget+consumption>limit:
            n.bow_change=True
            n.constraint_flags.append("bow_budget_forced_change")
            report.forced_bow_changes+=1
            report.issues.append(ConstraintIssue(
                "info","bow_budget_forced_change",n.part,n.start_tick,[n.source_id],
                f"estimated connected bow budget {budget+consumption:.2f}>{limit:.2f} beats"
            ))
            budget=0.0
        if n.bow_change:budget=0.0
        budget+=consumption
        n.bow_budget=min(1.5,budget/limit)
        report.max_risk=max(report.max_risk,min(1.0,n.bow_budget))
        prev=n

def _assignment_for_multistop(part,notes):
    """Return a distinct-string assignment if a simultaneous stop is ergonomically plausible."""
    notes=sorted(notes,key=lambda n:n.pitch)
    cands=[feasible_fingerings(part,n.pitch) for n in notes]
    if any(not c for c in cands):return None
    best=None;best_cost=inf

    def rec(i,used,acc,cost):
        nonlocal best,best_cost
        if i==len(notes):
            strings=sorted(x[0] for x in acc)
            # A bowed simultaneous stop must occupy a contiguous set of strings.
            if any((b-a)!=1 for a,b in zip(strings,strings[1:])):return
            fingers=[x[1] for x in acc if x[1]>0]
            span=(max(fingers)-min(fingers)) if len(fingers)>=2 else 0
            if span>MAX_STOP_SPAN[part]:return
            if cost<best_cost:best_cost=cost;best=list(acc)
            return
        for s,f in cands[i]:
            if s in used:continue
            c=cost+(f*.03)+(0.22 if f==0 and (notes[i].stack&8) else 0)
            if c>=best_cost:continue
            rec(i+1,used|{s},acc+[(s,f)],c)
    rec(0,set(),[],0.0)
    return best

def _simultaneous_groups(g,report):
    for part in range(4):
        starts={}
        for n in g.notes:
            if n.part==part:starts.setdefault(n.start_tick,[]).append(n)
        gid=0
        for tick,grp in sorted(starts.items()):
            if len(grp)<2:continue
            # Only notes that actually overlap in duration belong to the stop/chord event.
            grp=sorted(grp,key=lambda n:n.pitch)
            if len(grp)<2:continue
            gid+=1
            assignment=_assignment_for_multistop(part,grp[:4]) if len(grp)<=4 else None
            feasible=assignment is not None and len(grp)==2
            multi_possible=assignment is not None and len(grp)<=4
            divisi_required=not feasible
            if feasible:
                # Actually adopt the distinct-string fingering and a shared desk/bow plan.
                shared_desk=min(int(n.divisi_desk) for n in grp)
                shared_bow=int(grp[0].bow_direction)
                shared_change=any(bool(n.bow_change) for n in grp)
                shared_pressure=sum(float(n.bow_pressure) for n in grp)/len(grp)
                shared_contact=sum(float(n.contact_point) for n in grp)/len(grp)
                for n,(s,finger) in zip(grp,assignment):
                    n.string_index=s;n.string_name=STRING_NAMES[part][s];n.finger_semitone=finger
                    n.position_index=0 if finger==0 else max(1,1+(finger-1)//4)
                    n.open_string=(finger==0);n.divisi_desk=shared_desk
                    n.bow_direction=shared_bow;n.bow_change=shared_change
                    n.bow_pressure=shared_pressure;n.contact_point=shared_contact
                    n.constraint_flags.append("double_stop_consolidated")
            rec={
                "part":part,"part_name":PARTS[part],"group_id":gid,"tick":tick,
                "pitches":[n.pitch for n in grp],"note_count":len(grp),
                "double_stop_feasible":bool(feasible),
                "multi_stop_geometric_feasible":bool(multi_possible),
                "performance_mode":"double_stop" if feasible else "divisi",
                "divisi_required":bool(divisi_required),
                "suggested_distinct_strings":[STRING_NAMES[part][x[0]] for x in assignment] if assignment else [],
            }
            report.simultaneous_groups.append(rec)
            for n in grp:
                n.multi_stop_group_id=gid
                n.multi_stop_feasible=bool(multi_possible)
                n.divisi_required=bool(divisi_required)
                if divisi_required:n.constraint_flags.append("divisi_required")
            if len(grp)>4:
                report.issues.append(ConstraintIssue(
                    "error","voice_density_exceeds_4x4_bus",part,tick,[n.source_id for n in grp],
                    f"{len(grp)} simultaneous notes exceed four independent expression lanes"
                ))
                report.unplayable_notes += len(grp)-4
            elif len(grp)==2 and not feasible:
                report.issues.append(ConstraintIssue(
                    "info","double_stop_not_preferred",part,tick,[n.source_id for n in grp],
                    "distinct-string hand-frame heuristic failed; keep divisi desks"
                ))

def solve_string_constraints(g):
    report=ConstraintReport()

    # Hard configured planning range.
    for n in g.notes:
        if n.pitch<MIN_PITCH[n.part] or n.pitch>MAX_PITCH[n.part] or not feasible_fingerings(n.part,n.pitch):
            n.playability_risk=1.0
            n.constraint_flags.append("configured_range_violation")
            report.unplayable_notes+=1
            report.max_risk=1.0
            report.issues.append(ConstraintIssue(
                "error","configured_range_violation",n.part,n.start_tick,[n.source_id],
                f"pitch {n.pitch} outside configured {PARTS[n.part]} planning range {MIN_PITCH[n.part]}..{MAX_PITCH[n.part]}"
            ))

    # Repair transitions and bow budget inside each explicit v4.1 lane.
    lanes={}
    for n in g.notes:
        lanes.setdefault((n.part,n.lane_channel),[]).append(n)
    for _,notes in lanes.items():
        notes.sort(key=lambda n:(n.start_tick,n.pitch))
        _repair_lane(notes,report)
        # Re-plan bow/portamento after repaired fingering, then enforce finite bow budget.
        plan_bowing(notes)
        plan_portamento(notes)
        _bow_budget_lane(notes,report)

    _simultaneous_groups(g,report)

    # Overall per-note risk after all repairs.
    for n in g.notes:
        n.playability_risk=max(
            float(n.playability_risk),
            float(n.transition_risk),
            min(1.0,float(n.bow_budget)),
            1.0 if "configured_range_violation" in n.constraint_flags else 0.0,
        )
        report.max_risk=max(report.max_risk,n.playability_risk)
    return g,report
