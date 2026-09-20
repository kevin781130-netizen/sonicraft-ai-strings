#!/usr/bin/env python3
from __future__ import annotations
"""Orchestrate the deterministic post-training Schema 8 release path.

This runner does not train models and does not collect listener responses. It only
chains existing evaluators/gates using one release-plan JSON so paths cannot drift
between commands. ``all`` stops fail-closed if human ABX evidence is still missing.
"""
import argparse,json,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SCRIPTS=ROOT/'training'/'scripts'


def load_plan(path:Path)->dict:
    p=json.loads(path.read_text(encoding='utf-8'))
    if int(p.get('schema',0))!=1:raise SystemExit('unsupported release plan schema')
    if p.get('codec') not in ('dac44','strings_vae64'):raise SystemExit('release plan codec must be dac44 or strings_vae64')
    if not isinstance(p.get('paths'),dict):raise SystemExit('release plan paths missing')
    return p


def resolve(root:Path,plan:dict,key:str)->Path:
    value=(plan.get('paths') or {}).get(key)
    if not value:raise SystemExit(f'release plan missing paths.{key}')
    p=Path(value);return p if p.is_absolute() else root/p


def run(cmd:list[str],dry:bool)->None:
    print('+',' '.join(str(x) for x in cmd))
    if dry:return
    subprocess.run(cmd,cwd=ROOT,check=True)


def eval_commands(root:Path,plan:dict)->list[list[str]]:
    held=resolve(root,plan,'heldout_transition_index');seed=str(int(plan.get('seed',260917)))
    pairs=(
        ('hq_baseline_checkpoint','hq_baseline_eval'),('hq_candidate_checkpoint','hq_candidate_eval'),
        ('compact_baseline_checkpoint','compact_baseline_eval'),('compact_candidate_checkpoint','compact_candidate_eval'),
    )
    return [[sys.executable,str(SCRIPTS/'evaluate_renderer_transitions.py'),'--checkpoint',str(resolve(root,plan,ck)),'--index',str(held),'--out',str(resolve(root,plan,out)),'--seed',seed]
            for ck,out in pairs]


def promotion_commands(root:Path,plan:dict)->list[list[str]]:
    curriculum=resolve(root,plan,'phrase_curriculum_report')
    pairs=(
        ('hq_baseline_eval','hq_candidate_eval','hq_transition_promotion'),
        ('compact_baseline_eval','compact_candidate_eval','compact_transition_promotion'),
    )
    return [[sys.executable,str(SCRIPTS/'build_transition_promotion.py'),'--baseline',str(resolve(root,plan,b)),'--candidate',str(resolve(root,plan,c)),
             '--curriculum',str(curriculum),'--out',str(resolve(root,plan,o))] for b,c,o in pairs]


def preflight_command(root:Path,plan:dict)->list[str]:
    return [sys.executable,str(SCRIPTS/'schema8_release_preflight.py'),
        '--provenance',str(resolve(root,plan,'training_provenance')),
        '--registry',str(resolve(root,plan,'registry')),
        '--metrics',str(resolve(root,plan,'release_metrics')),
        '--sound-forge-report',str(resolve(root,plan,'sound_forge_report')),
        '--codec-tournament',str(resolve(root,plan,'codec_tournament')),
        '--codec-abx-report',str(resolve(root,plan,'codec_abx_report')),
        '--acoustic-segments',str(resolve(root,plan,'acoustic_segments')),
        '--generated-real-abx',str(resolve(root,plan,'generated_real_abx')),
        '--acoustic-promotion',str(resolve(root,plan,'acoustic_promotion')),
        '--phrase-curriculum-report',str(resolve(root,plan,'phrase_curriculum_report')),
        '--phrase-finetune-index',str(resolve(root,plan,'phrase_finetune_index')),
        '--heldout-index',str(resolve(root,plan,'heldout_transition_index')),
        '--hq-transition-promotion',str(resolve(root,plan,'hq_transition_promotion')),
        '--compact-transition-promotion',str(resolve(root,plan,'compact_transition_promotion')),
        '--hq-checkpoint',str(resolve(root,plan,'hq_candidate_checkpoint')),
        '--compact-checkpoint',str(resolve(root,plan,'compact_candidate_checkpoint')),
        '--codec',str(plan['codec'])]


def seal_commands(root:Path,plan:dict)->list[list[str]]:
    curriculum=resolve(root,plan,'phrase_curriculum_report')
    return [
        [sys.executable,str(SCRIPTS/'seal_transition_promotion.py'),'--checkpoint',str(resolve(root,plan,'hq_candidate_checkpoint')),'--promotion',str(resolve(root,plan,'hq_transition_promotion')),'--curriculum',str(curriculum)],
        [sys.executable,str(SCRIPTS/'seal_transition_promotion.py'),'--checkpoint',str(resolve(root,plan,'compact_candidate_checkpoint')),'--promotion',str(resolve(root,plan,'compact_transition_promotion')),'--curriculum',str(curriculum)],
    ]


def manifest_command(root:Path,plan:dict)->list[str]:
    return [sys.executable,str(SCRIPTS/'build_release_model_manifest.py'),'--schema','8','--model-dir',str(resolve(root,plan,'model_dir')),
        '--provenance',str(resolve(root,plan,'training_provenance')),'--registry',str(resolve(root,plan,'registry')),
        '--metrics',str(resolve(root,plan,'release_metrics')),'--codec',str(plan['codec']),
        '--sound-forge-report',str(resolve(root,plan,'sound_forge_report')),'--codec-tournament',str(resolve(root,plan,'codec_tournament')),
        '--codec-abx-report',str(resolve(root,plan,'codec_abx_report')),'--acoustic-segments',str(resolve(root,plan,'acoustic_segments')),
        '--generated-real-abx',str(resolve(root,plan,'generated_real_abx')),'--acoustic-promotion',str(resolve(root,plan,'acoustic_promotion')),
        '--phrase-curriculum-report',str(resolve(root,plan,'phrase_curriculum_report')),
        '--hq-transition-promotion',str(resolve(root,plan,'hq_transition_promotion')),
        '--compact-transition-promotion',str(resolve(root,plan,'compact_transition_promotion')),'--approve']


def gate_command(root:Path,plan:dict)->list[str]:
    return [sys.executable,str(SCRIPTS/'commercial_release_gate.py'),'--root',str(root),'--model-dir',str(resolve(root,plan,'model_dir'))]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',required=True)
    ap.add_argument('--root',default='.')
    ap.add_argument('--phase',choices=('evaluate','promote','preflight','seal','manifest','gate','all'),default='all')
    ap.add_argument('--dry-run',action='store_true')
    a=ap.parse_args();root=Path(a.root).resolve();plan_path=Path(a.plan);plan_path=plan_path if plan_path.is_absolute() else root/plan_path
    plan=load_plan(plan_path)

    phase=a.phase
    if phase in ('evaluate','all'):
        for cmd in eval_commands(root,plan):run(cmd,a.dry_run)
    if phase in ('promote','all'):
        for cmd in promotion_commands(root,plan):run(cmd,a.dry_run)
    if phase in ('preflight','seal','all'):
        # Sealing is never allowed through this runner without the read-only exact-file preflight first.
        run(preflight_command(root,plan),a.dry_run)
    if phase in ('seal','all'):
        for cmd in seal_commands(root,plan):run(cmd,a.dry_run)
    if phase in ('manifest','all'):run(manifest_command(root,plan),a.dry_run)
    if phase in ('gate','all'):run(gate_command(root,plan),a.dry_run)
    print('Schema 8 post-GPU phase complete:',phase,'(dry-run)' if a.dry_run else '')

if __name__=='__main__':main()
