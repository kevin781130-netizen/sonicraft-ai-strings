from __future__ import annotations
"""Dependency-light smoke for Schema 8 production plan/status/orchestration."""
import json,subprocess,sys,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'training'/'scripts'

STATIC=(
    'registry','phrase_finetune_index','phrase_curriculum_report','heldout_transition_index','training_provenance',
    'release_metrics','sound_forge_report','codec_tournament','codec_abx_report','acoustic_segments','acoustic_promotion',
    'hq_baseline_checkpoint','compact_baseline_checkpoint',
)
TRANSITION=('hq_baseline_eval','hq_candidate_eval','compact_baseline_eval','compact_candidate_eval','hq_transition_promotion','compact_transition_promotion')


def run(args,expected=0):
    p=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    if p.returncode!=expected:raise AssertionError(f'rc {p.returncode} != {expected}\n{p.stdout}\n{p.stderr}')
    return p


def write(path:Path,data=b'x'):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)


def status(root:Path,plan:Path)->dict:
    out=run([sys.executable,str(SCRIPTS/'schema8_release_status.py'),'--root',str(root),'--plan',str(plan)])
    return json.loads(out.stdout)


def main():
    with tempfile.TemporaryDirectory() as td:
        d=Path(td);paths={k:f'artifacts/{k}.dat' for k in STATIC+TRANSITION}
        paths.update({
            'hq_candidate_checkpoint':'Models/ballad_renderer_hq_v20_best.pt',
            'compact_candidate_checkpoint':'Models/ballad_renderer_frontier_v20_shortcut.pt',
            'generated_real_abx':'evidence/generated_real_abx.json','abx_packet':'evidence/abx_packet','abx_responses':'evidence/abx_responses',
            'model_dir':'Models','release_manifest':'Models/release_model_manifest.json',
        })
        plan=d/'plan.json';plan.write_text(json.dumps({'schema':1,'codec':'strings_vae64','seed':260917,'paths':paths},indent=2),encoding='utf-8')
        for k in STATIC:write(d/paths[k])
        assert status(d,plan)['stage']=='WAITING_FOR_GPU_TRAINING'
        write(d/paths['hq_candidate_checkpoint']);write(d/paths['compact_candidate_checkpoint'])
        assert status(d,plan)['stage']=='WAITING_FOR_TRANSITION_EVAL_OR_PROMOTION'
        for k in TRANSITION:write(d/paths[k])
        assert status(d,plan)['stage']=='WAITING_FOR_HUMAN_ABX'
        write(d/paths['generated_real_abx'],b'{}')
        assert status(d,plan)['stage']=='READY_FOR_SCHEMA8_FINALIZATION'
        write(d/paths['release_manifest'],b'{}')
        assert status(d,plan)['stage']=='RELEASE_MANIFEST_PRESENT'

        dry=run([sys.executable,str(SCRIPTS/'run_schema8_post_gpu.py'),'--root',str(d),'--plan',str(plan),'--phase','all','--dry-run']).stdout
        order=['evaluate_renderer_transitions.py','build_transition_promotion.py','schema8_release_preflight.py','seal_transition_promotion.py','build_release_model_manifest.py','commercial_release_gate.py']
        positions=[dry.find(x) for x in order]
        assert all(x>=0 for x in positions),dry
        assert positions==sorted(positions),dry
        seal_dry=run([sys.executable,str(SCRIPTS/'run_schema8_post_gpu.py'),'--root',str(d),'--plan',str(plan),'--phase','seal','--dry-run']).stdout
        assert seal_dry.find('schema8_release_preflight.py')<seal_dry.find('seal_transition_promotion.py')

    print('Schema 8 release plan smoke: PASS')

if __name__=='__main__':main()
