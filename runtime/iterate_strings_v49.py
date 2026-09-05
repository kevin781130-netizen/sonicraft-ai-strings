"""SONICRAFT v4.9 post-render Audio Judge -> Repair Policy -> next-round orchestrator.

This script does not pretend to drive Cubase/Studio One or a missing acoustic model. It consumes
the four actual rendered WAVs. Only an accepted objective Audio Judge result updates repair policy.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,sys
import numpy as np

from audio_io_v49 import load_render_set_v49
from midi_judge_adapter_v49 import midi_to_judge_events_v49
from audio_take_judge_v37 import judge_take,score_dict
from string_repair_policy_v49 import RepairPolicyMemoryV49
from compile_musicxml_strings_v49 import compile_file

SLOTS="ABCD"
MAX_ROUND=6

def _resolve_renders(queue_path,queue,render_dir=None,explicit=None):
    qdir=Path(queue_path).parent
    out={}
    explicit=explicit or {}
    for slot in SLOTS:
        if explicit.get(slot):
            p=Path(explicit[slot])
        elif render_dir:
            rd=Path(render_dir)
            expected=queue["slots"][slot]["expected_render"]
            p=rd/expected
            if not p.exists():
                simple=rd/f"{slot}.wav"
                if simple.exists():p=simple
        else:
            p=qdir/queue["slots"][slot]["expected_render"]
        if not p.exists():raise FileNotFoundError(f"missing render {slot}: {p}")
        out[slot]=p
    return out

def judge_render_set_v49(queue_path,render_dir=None,explicit=None):
    queue_path=Path(queue_path);queue=json.loads(queue_path.read_text(encoding="utf-8"))
    if queue.get("version")!="4.9":raise ValueError("judge queue is not v4.9")
    paths=_resolve_renders(queue_path,queue,render_dir,explicit)
    audios,sr,frames=load_render_set_v49([paths[s] for s in SLOTS])
    qdir=queue_path.parent
    scores={}
    for slot,audio in zip(SLOTS,audios):
        midi=qdir/queue["slots"][slot]["midi"]
        if not midi.exists():raise FileNotFoundError(f"missing candidate MIDI {slot}: {midi}")
        events=midi_to_judge_events_v49(midi,sr,frames)
        sc=judge_take(audio,sr,events,0,frames)
        scores[slot]=sc
    ranking=sorted(SLOTS,key=lambda s:scores[s].overall,reverse=True)
    winner=ranking[0];runner=ranking[1]
    margin=float(scores[winner].overall-scores[runner].overall)
    return queue,paths,sr,frames,scores,winner,runner,margin

def iterate_v49(queue_path,render_dir=None,explicit=None,score_override=None,no_regenerate=False):
    queue,paths,sr,frames,scores,winner,runner,margin=judge_render_set_v49(queue_path,render_dir,explicit)
    policy_path=Path(queue["policy_path"])
    mem=RepairPolicyMemoryV49(policy_path)
    before=mem.snapshot()
    stale=(before.generation!=int(queue["policy_generation"]) or before.profile_hash!=str(queue["policy_hash"]))

    winner_score=scores[winner]
    if stale:
        learn={"learned":False,"reason":"stale_policy","snapshot":before}
    else:
        learn=mem.learn(winner,margin,winner_score.safety,winner_score.overall)
    after=mem.snapshot()

    next_queue=None
    round_index=int(queue.get("round_index",1))
    regenerated=False
    regenerate_reason="not_learned"
    if learn.get("learned") and not no_regenerate:
        if round_index>=MAX_ROUND:
            regenerate_reason="round_cap"
        else:
            src=Path(score_override) if score_override else Path(queue["source_score"])
            if not src.exists():raise FileNotFoundError(f"source score for next round not found: {src}")
            out_dir=Path(queue_path).parent
            next_out=out_dir/(src.stem+f"_SONICRAFT_STRINGS_v49_R{round_index+1}.mid")
            r=compile_file(src,next_out,policy_path,round_index+1)
            next_queue=str(r["judge_queue_json"])
            regenerated=True;regenerate_reason="accepted_learning"
    elif no_regenerate:
        regenerate_reason="disabled"

    report={
        "schema":1,"version":"4.9",
        "input_queue":str(Path(queue_path).resolve()),
        "round_index":round_index,
        "sample_rate":sr,"frames":frames,
        "renders":{s:str(paths[s]) for s in SLOTS},
        "audio_judge":{
            "winner":winner,"runner_up":runner,"margin":round(margin,9),
            "scores":{s:score_dict(scores[s]) for s in SLOTS},
        },
        "structural_recommendation":queue.get("structural_recommendation"),
        "critic_audio_agree":queue.get("structural_recommendation")==winner,
        "policy_before":{"generation":before.generation,"hash":before.profile_hash,
                         "confidence":before.confidence,"values":before.values},
        "learning":{
            "accepted":bool(learn.get("learned")),"reason":learn.get("reason"),
            "winner_safety":winner_score.safety,"winner_overall":winner_score.overall,
        },
        "policy_after":{"generation":after.generation,"hash":after.profile_hash,
                        "confidence":after.confidence,"values":after.values},
        "next_round":{"generated":regenerated,"reason":regenerate_reason,"judge_queue":next_queue},
        "authority_note":"v4.9 policy learns from objective Audio Judge only; personal Favorite/Commit memory remains separate.",
    }
    rp=Path(queue_path).with_name(Path(queue_path).stem+f".iteration_result_R{round_index}.json")
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report,rp

def main(argv=None):
    ap=argparse.ArgumentParser(description="Judge four rendered v4.9 candidates, gated-learn repair policy, and generate next round.")
    ap.add_argument("judge_queue",type=Path)
    ap.add_argument("render_dir",type=Path,nargs="?")
    ap.add_argument("--a",type=Path);ap.add_argument("--b",type=Path);ap.add_argument("--c",type=Path);ap.add_argument("--d",type=Path)
    ap.add_argument("--score",type=Path,help="override source score path for next round")
    ap.add_argument("--no-regenerate",action="store_true")
    a=ap.parse_args(argv)
    explicit={k.upper():v for k,v in {"a":a.a,"b":a.b,"c":a.c,"d":a.d}.items() if v}
    try:r,rp=iterate_v49(a.judge_queue,a.render_dir,explicit,a.score,a.no_regenerate)
    except Exception as ex:print("ERROR:",ex,file=sys.stderr);return 2
    j=r["audio_judge"];l=r["learning"];n=r["next_round"]
    print("SONICRAFT v4.9 Audio Judge -> Repair Policy iteration OK")
    print("Winner:",j["winner"],"margin:",round(j["margin"],4))
    print("Structural recommendation:",r["structural_recommendation"],"agree:",r["critic_audio_agree"])
    print("Learning:",l["accepted"],l["reason"])
    print("Policy generation:",r["policy_after"]["generation"],"confidence:",round(r["policy_after"]["confidence"],4))
    print("Next round:",n["generated"],n["judge_queue"] or n["reason"])
    print("Report:",rp)
    return 0
if __name__=="__main__":raise SystemExit(main())
