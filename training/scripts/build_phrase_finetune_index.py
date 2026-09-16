#!/usr/bin/env python3
from __future__ import annotations
"""Build a renderer fine-tune index with lane-locked phrase supervision.

This script never changes the global REAL/MODELED ratio.  It only annotates
relative source weights inside the modeled lane; train_ballad_renderer.py still
uses string_source_mixer.py as the authority for the 80/20 probability lock.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phrase_curriculum import curriculum_sweep_audit, with_phrase_lane_weights
from source_policy import validate_index
from string_source_mixer import load_registry, mixture_audit, build_curriculum_weights


def read_jsonl(path: str | Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base-index',required=True,help='Existing rights-gated renderer latent index (real + optional modeled).')
    ap.add_argument('--phrase-index',required=True,help='Clean-room phrase latent index produced by encode_*_latents.py.')
    ap.add_argument('--out',default='datasets/processed/phrase_finetune/index.jsonl')
    ap.add_argument('--report',default='datasets/processed/phrase_finetune/curriculum_report.json')
    ap.add_argument('--registry',default='training/dataset_registry.json')
    ap.add_argument('--phrase-modeled-share',type=float,default=.65,help='Target phrase share inside the modeled lane only.')
    ap.add_argument('--real-ratio',type=float,default=.80);ap.add_argument('--modeled-ratio',type=float,default=.20)
    a=ap.parse_args()

    # Both inputs must already satisfy the repository's release-source policy.
    validate_index(a.base_index,a.registry); validate_index(a.phrase_index,a.registry)
    base=read_jsonl(a.base_index); phrase=read_jsonl(a.phrase_index)
    if not phrase or not all(str(r.get('phrase_family') or '').strip() for r in phrase):
        raise SystemExit('phrase index contains rows without phrase_family metadata')
    rows=base+phrase; registry=load_registry(a.registry)
    rows=with_phrase_lane_weights(rows,registry,target_modeled_phrase_share=a.phrase_modeled_share)

    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('\n'.join(json.dumps(r,ensure_ascii=False,sort_keys=True) for r in rows)+'\n',encoding='utf-8')

    sweep=curriculum_sweep_audit(rows,registry,real_ratio=a.real_ratio,modeled_ratio=a.modeled_ratio)
    mid=build_curriculum_weights(rows,registry,a.real_ratio,a.modeled_ratio,progress=.5,require_modeled=True)
    report={
        'schema':1,'version':'phrase_finetune_index_v1','base_index':str(Path(a.base_index)),
        'phrase_index':str(Path(a.phrase_index)),'output_index':str(out),'base_rows':len(base),'phrase_rows':len(phrase),
        'total_rows':len(rows),'requested_real_ratio':a.real_ratio,'requested_modeled_ratio':a.modeled_ratio,
        'target_phrase_share_within_modeled':a.phrase_modeled_share,
        'midpoint_mixture':mixture_audit(rows,mid,registry),'curriculum_sweep':sweep,
        'policy':'phrase weighting is lane-internal; global REAL/MODELED probability remains controlled by string_source_mixer',
    }
    rp=Path(a.report);rp.parent.mkdir(parents=True,exist_ok=True);rp.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=='__main__':main()
