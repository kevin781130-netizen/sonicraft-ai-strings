#!/usr/bin/env python3
from __future__ import annotations
"""Report production readiness for a Schema 8 release plan.

This command is intentionally read-only and dependency-light. It does not replace
preflight or release gates; it answers one operational question: what artifact is
missing next?
"""
import argparse,hashlib,json
from pathlib import Path

FILE_GROUPS={
    'static_inputs':(
        'registry','phrase_finetune_index','phrase_curriculum_report','heldout_transition_index',
        'training_provenance','release_metrics','sound_forge_report','codec_tournament',
        'codec_abx_report','acoustic_segments','acoustic_promotion',
        'hq_baseline_checkpoint','compact_baseline_checkpoint',
    ),
    'gpu_training_outputs':('hq_candidate_checkpoint','compact_candidate_checkpoint'),
    'transition_evidence':(
        'hq_baseline_eval','hq_candidate_eval','compact_baseline_eval','compact_candidate_eval',
        'hq_transition_promotion','compact_transition_promotion',
    ),
    'human_abx':('generated_real_abx',),
    'final_release':('release_manifest',),
}
OPTIONAL_DIRS=('abx_packet','abx_responses','model_dir')


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def resolve(root:Path,value:str|None)->Path|None:
    if not value:return None
    p=Path(value)
    return p if p.is_absolute() else root/p


def describe(path:Path|None)->dict:
    if path is None:return {'configured':False,'exists':False}
    if not path.exists():return {'configured':True,'exists':False,'path':str(path)}
    if path.is_file():return {'configured':True,'exists':True,'kind':'file','path':str(path),'bytes':path.stat().st_size,'sha256':sha256(path)}
    return {'configured':True,'exists':True,'kind':'directory','path':str(path)}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',required=True)
    ap.add_argument('--root',default='.')
    ap.add_argument('--out')
    a=ap.parse_args();root=Path(a.root).resolve();plan_path=resolve(root,a.plan)
    if plan_path is None or not plan_path.is_file():raise SystemExit('release plan missing: '+str(plan_path))
    plan=json.loads(plan_path.read_text(encoding='utf-8'))
    if int(plan.get('schema',0))!=1:raise SystemExit('unsupported release plan schema')
    paths=dict(plan.get('paths') or {})
    artifacts={k:describe(resolve(root,paths.get(k))) for group in FILE_GROUPS.values() for k in group}
    artifacts.update({k:describe(resolve(root,paths.get(k))) for k in OPTIONAL_DIRS})

    missing_by_group={g:[k for k in keys if not artifacts[k]['exists']] for g,keys in FILE_GROUPS.items()}
    if missing_by_group['static_inputs']:
        stage='WAITING_FOR_STATIC_INPUTS'; blockers=missing_by_group['static_inputs']
    elif missing_by_group['gpu_training_outputs']:
        stage='WAITING_FOR_GPU_TRAINING'; blockers=missing_by_group['gpu_training_outputs']
    elif missing_by_group['transition_evidence']:
        stage='WAITING_FOR_TRANSITION_EVAL_OR_PROMOTION'; blockers=missing_by_group['transition_evidence']
    elif missing_by_group['human_abx']:
        stage='WAITING_FOR_HUMAN_ABX'; blockers=missing_by_group['human_abx']
    elif missing_by_group['final_release']:
        stage='READY_FOR_SCHEMA8_FINALIZATION'; blockers=missing_by_group['final_release']
    else:
        stage='RELEASE_MANIFEST_PRESENT'; blockers=[]

    report={'schema':1,'plan':str(plan_path),'codec':plan.get('codec'),'stage':stage,'blockers':blockers,
            'missing_by_group':missing_by_group,'artifacts':artifacts,
            'note':'Presence/status report only. Schema 8 preflight, seals, manifest validation and commercial gate remain authoritative.'}
    text=json.dumps(report,indent=2,sort_keys=True)
    if a.out:
        p=resolve(root,a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text+'\n',encoding='utf-8')
    print(text)

if __name__=='__main__':main()
