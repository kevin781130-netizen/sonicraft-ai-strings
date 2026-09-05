"""SONICRAFT v4.4 Ensemble Bow & Phrase Coordination Solver.

Full-score strings-only coordination layer above v4.3 constraints.

It coordinates compatible tutti attacks without erasing written notation:
- phrase segmentation per explicit string voice lane,
- cross-part attack clusters,
- bow-direction agreement for unforced bowed notes,
- shared bow-change anchors at ensemble phrase attacks,
- deterministic small attack spread,
- phrase-end breathing,
- bow-mark conflict reporting,
- role metadata (lead / inner / foundation).

No acoustic model or score pitches are invented here.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict,field
from score_expression_graph_v40 import PARTS,PPQ

ATTACK_MAX_MS=8.0
BREATH_MAX_MS=20.0
CLUSTER_TICKS=max(12,PPQ//32) # 1/32 quarter-note tolerance

@dataclass
class EnsembleIssue:
    severity:str
    kind:str
    tick:int
    parts:list[int]=field(default_factory=list)
    source_ids:list[str]=field(default_factory=list)
    detail:str=""

@dataclass
class EnsembleReport:
    issues:list[EnsembleIssue]=field(default_factory=list)
    groups:list[dict]=field(default_factory=list)
    phrases:list[dict]=field(default_factory=list)
    coordinated_attacks:int=0
    coordinated_bow_directions:int=0
    coordinated_bow_changes:int=0
    phrase_breaths:int=0
    bow_conflicts:int=0
    max_attack_spread_ms:float=0.0
    def as_dict(self):
        return {
            "issues":[asdict(x) for x in self.issues],
            "groups":self.groups,
            "phrases":self.phrases,
            "coordinated_attacks":self.coordinated_attacks,
            "coordinated_bow_directions":self.coordinated_bow_directions,
            "coordinated_bow_changes":self.coordinated_bow_changes,
            "phrase_breaths":self.phrase_breaths,
            "bow_conflicts":self.bow_conflicts,
            "max_attack_spread_ms":round(float(self.max_attack_spread_ms),6),
        }

def _bpm_at(g,tick):
    bpm=120.0
    for x in sorted(g.tempos,key=lambda y:int(y["tick"])):
        if int(x["tick"])>int(tick):break
        bpm=float(x["bpm"])
    return max(24.0,bpm)

def _is_bowed(n):
    return n.base_art!=8

def _is_connected(prev,n):
    return prev is not None and n.start_tick-prev.end_tick<=max(40,PPQ//48) and (
        prev.slur or n.slur or (prev.stack&2) or (n.stack&2) or prev.base_art in (1,2) or n.base_art in (1,2)
    )

def _forced_bow(n):
    if "down-bow" in n.technical:return 0
    if "up-bow" in n.technical:return 1
    return None

def _is_strong_attack(n):
    return bool((n.stack&1) or n.base_art in (4,5,6) or n.velocity>=100)

def _phrase_segmentation(g,report):
    phrase_id=0
    phrase_starts=set()
    lanes={}
    for n in g.notes:lanes.setdefault((n.part,n.lane_channel),[]).append(n)
    for (part,lane),notes in sorted(lanes.items()):
        notes.sort(key=lambda n:(n.start_tick,n.pitch))
        prev=None;current=None
        for n in notes:
            new_phrase=(prev is None)
            if prev is not None:
                gap=max(0,n.start_tick-prev.end_tick)
                new_phrase = gap>=PPQ//2 or (gap>=PPQ//6 and not _is_connected(prev,n))
            if new_phrase:
                phrase_id+=1;current=phrase_id;phrase_starts.add(n.source_id)
            n.ensemble_phrase_id=current
            prev=n
        if notes:
            report.phrases.append({
                "phrase_id":notes[0].ensemble_phrase_id if len({n.ensemble_phrase_id for n in notes})==1 else None,
                "part":part,"part_name":PARTS[part],"lane_channel":lane,
                "first_tick":notes[0].start_tick,"last_tick":notes[-1].end_tick,
                "phrase_ids":sorted({n.ensemble_phrase_id for n in notes}),
            })
    return phrase_starts,lanes

def _apply_phrase_breathing(g,lanes,report):
    for _,notes in lanes.items():
        notes.sort(key=lambda n:(n.start_tick,n.pitch))
        for i,n in enumerate(notes):
            nxt=notes[i+1] if i+1<len(notes) else None
            phrase_end=nxt is None or nxt.ensemble_phrase_id!=n.ensemble_phrase_id
            if not phrase_end:continue
            # Ties/slurs across the boundary win over automatic breathing.
            if nxt is not None and _is_connected(n,nxt):continue
            if n.tie_start:continue
            bpm=_bpm_at(g,n.end_tick)
            quarter_ms=60000.0/bpm
            breath=min(BREATH_MAX_MS,max(5.0,quarter_ms*.026))
            if n.base_art in (5,6,8):breath=min(breath,7.0)
            if n.stack&8:breath=min(BREATH_MAX_MS,breath+3.0)
            n.ensemble_breath_ms=breath
            n.ensemble_coordination_flags.append("phrase_breath")
            report.phrase_breaths+=1

def _cluster_onsets(g):
    notes=sorted(g.notes,key=lambda n:(n.start_tick,n.part,n.pitch))
    groups=[];cur=[];anchor=None
    for n in notes:
        if anchor is None or n.start_tick-anchor<=CLUSTER_TICKS:
            if anchor is None:anchor=n.start_tick
            cur.append(n)
        else:
            groups.append((anchor,cur));anchor=n.start_tick;cur=[n]
    if cur:groups.append((anchor,cur))
    return groups

def _role_by_part(group):
    by={}
    for n in group:by.setdefault(n.part,[]).append(n.pitch)
    if not by:return {}
    means={p:sum(v)/len(v) for p,v in by.items()}
    hi=max(means,key=means.get);lo=min(means,key=means.get)
    roles={p:"inner" for p in means}
    roles[hi]="lead"
    if lo!=hi:roles[lo]="foundation"
    return roles

def _part_attack_offset_ms(part,desk,strong=False):
    # Deterministic orchestral spread: tiny enough to preserve authored rhythm.
    part_base=(-1.35,-0.45,0.45,1.35)[max(0,min(3,int(part)))]
    desk_delta=(-.45,-.15,.15,.45)[max(0,min(3,int(desk)))]
    scale=.55 if strong else 1.0
    return max(-ATTACK_MAX_MS,min(ATTACK_MAX_MS,(part_base+desk_delta)*scale))

def coordinate_string_ensemble(g):
    report=EnsembleReport()
    phrase_starts,lanes=_phrase_segmentation(g,report)
    _apply_phrase_breathing(g,lanes,report)

    previous_ensemble_direction=1
    group_id=0
    for tick,group in _cluster_onsets(g):
        parts=sorted({n.part for n in group})
        if len(parts)<2:continue
        group_id+=1
        roles=_role_by_part(group)
        bowed=[n for n in group if _is_bowed(n)]
        forced={_forced_bow(n) for n in bowed if _forced_bow(n) is not None}
        forced.discard(None)
        conflict=(0 in forced and 1 in forced)
        if conflict:
            report.bow_conflicts+=1
            report.issues.append(EnsembleIssue(
                "warning","explicit_bow_direction_conflict",tick,parts,[n.source_id for n in bowed],
                "simultaneous parts contain both forced down-bow and forced up-bow; written marks preserved"
            ))
        if forced and not conflict:
            target=next(iter(forced))
        else:
            strong_metric=(tick%PPQ)==0
            target=0 if strong_metric else 1-previous_ensemble_direction
        previous_ensemble_direction=target

        strong=any(_is_strong_attack(n) for n in group)
        phrase_anchor=sum(1 for n in group if n.source_id in phrase_starts)>=max(2,len(parts)//2)
        sync_bow_change=bool(strong or phrase_anchor)

        for n in group:
            n.ensemble_group_id=group_id
            n.ensemble_role=roles.get(n.part,"inner")
            n.ensemble_bow_sync=bool(_is_bowed(n) and not conflict)
            n.ensemble_attack_offset_ms=_part_attack_offset_ms(n.part,n.divisi_desk,strong)
            report.max_attack_spread_ms=max(report.max_attack_spread_ms,abs(n.ensemble_attack_offset_ms))
            n.ensemble_coordination_flags.append("ensemble_attack_spread")
            report.coordinated_attacks+=1

            if _is_bowed(n):
                forced_dir=_forced_bow(n)
                if forced_dir is None and not conflict:
                    if n.bow_direction!=target:
                        n.bow_direction=target
                        n.ensemble_coordination_flags.append("ensemble_bow_direction")
                        report.coordinated_bow_directions+=1
                # Never cut through an explicit/connected slur just to line up bow changes.
                if sync_bow_change and n.source_id in phrase_starts and not n.bow_change:
                    n.bow_change=True
                    n.ensemble_coordination_flags.append("ensemble_bow_change")
                    report.coordinated_bow_changes+=1

        report.groups.append({
            "group_id":group_id,"tick":tick,"parts":parts,"part_names":[PARTS[p] for p in parts],
            "note_count":len(group),"bowed_note_count":len(bowed),"target_bow":"down" if target==0 else "up",
            "explicit_bow_conflict":conflict,"phrase_anchor":phrase_anchor,"strong_attack":strong,
            "roles":{PARTS[p]:r for p,r in roles.items()},
            "attack_offsets_ms":{n.source_id:round(float(n.ensemble_attack_offset_ms),6) for n in group},
        })

    # Per-note coordination risk remains transparent.
    for n in g.notes:
        risk=0.0
        if "ensemble_attack_spread" in n.ensemble_coordination_flags:
            risk=max(risk,abs(n.ensemble_attack_offset_ms)/ATTACK_MAX_MS*.18)
        if n.ensemble_bow_sync and _forced_bow(n) is not None:
            risk=max(risk,.08)
        n.ensemble_coordination_risk=max(0.0,min(1.0,risk))
    return g,report
