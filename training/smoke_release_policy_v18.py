from __future__ import annotations
import json, subprocess, sys, tempfile
import torch
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from release_integrity import verify_release_manifest, IntegrityError

POLICY={
    'real_probability':.8,'modeled_probability':.2,
    'modeled_timbre_anchor':False,'modeled_adversarial_target':False,
    'curriculum':'lane_locked_quality_coverage_v18','cleanroom_modeled_only':True,
}
METRICS={
    'product':'SONICRAFT AI Strings Q4','release_pass':True,
    'midi_lock_pass':True,'vibrato_monotonic_pass':True,'tempo_transition_pass':True,
    'dropout_fallback_pass':True,'abx_pass':True,
    'abx':{'generated_identification_accuracy':.55,'target_max_accuracy':.60,'listener_count':3,'trial_count':20},
}

def must_reject(model_dir:Path, manifest:dict, policy:dict):
    bad=dict(manifest); bad['training_policy']=policy
    (model_dir/'release_model_manifest.json').write_text(json.dumps(bad),encoding='utf-8')
    try: verify_release_manifest(model_dir)
    except IntegrityError: return
    raise AssertionError('invalid schema-5 training policy was accepted')

def main():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); md=td/'models'; out=td/'packs'; md.mkdir()
        for n in ('ballad_renderer_hq_v18_best.pt','ballad_renderer_frontier_v18_shortcut.pt','strings_vae64_decoder_v18.pt'):
            torch.save({'training_mix':{'real':.8,'modeled':.2,'curriculum':'lane_locked_quality_coverage_v18'},'model':{}},md/n)
        prov=td/'prov.json'; metrics=td/'metrics.json'
        prov.write_text(json.dumps({'sources':[{'dataset':'tinysol'},{'dataset':'synthetic_cleanroom_bowed_v18'}],'training_policy':POLICY}),encoding='utf-8')
        metrics.write_text(json.dumps(METRICS),encoding='utf-8')
        subprocess.run([sys.executable,str(ROOT/'training/scripts/build_release_model_manifest.py'),'--model-dir',str(md),'--provenance',str(prov),'--metrics',str(metrics),'--approve','--codec','strings_vae64','--schema','5'],check=True,stdout=subprocess.DEVNULL)
        ok=verify_release_manifest(md); assert ok['verified']
        # Checkpoint metadata itself is part of the proof, not only the provenance JSON.
        bad_md=td/'bad_models'; bad_md.mkdir()
        for src in md.glob('*.pt'):
            import shutil; shutil.copy2(src,bad_md/src.name)
        torch.save({'training_mix':{'real':.70,'modeled':.30,'curriculum':'lane_locked_quality_coverage_v18'},'model':{}},bad_md/'ballad_renderer_frontier_v18_shortcut.pt')
        bad_run=subprocess.run([sys.executable,str(ROOT/'training/scripts/build_release_model_manifest.py'),'--model-dir',str(bad_md),'--provenance',str(prov),'--metrics',str(metrics),'--approve','--codec','strings_vae64','--schema','5'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        assert bad_run.returncode!=0, 'checkpoint REAL/MODEL drift was accepted'
        m=json.loads((md/'release_model_manifest.json').read_text(encoding='utf-8')); assert m['schema']==5 and m['training_policy']==POLICY
        must_reject(md,m,dict(POLICY,real_probability=.79,modeled_probability=.21))
        must_reject(md,m,dict(POLICY,modeled_timbre_anchor=True))
        # restore valid manifest for the independent commercial gate / profile pack path
        (md/'release_model_manifest.json').write_text(json.dumps(m),encoding='utf-8')
        subprocess.run([sys.executable,str(ROOT/'training/scripts/commercial_release_gate.py'),'--root',str(ROOT),'--model-dir',str(md)],check=True,stdout=subprocess.DEVNULL)
        subprocess.run([sys.executable,str(ROOT/'training/scripts/build_profile_model_packs.py'),'--model-dir',str(md),'--out-dir',str(out)],check=True,stdout=subprocess.DEVNULL)
        names={p.name for p in out.glob('*.zip')}
        assert 'SONICRAFT_AI_Strings_ModelPack_STANDARD_v1.8.0.zip' in names
        assert 'SONICRAFT_AI_Strings_ModelPack_FULL_HQ_v1.8.0.zip' in names
    print('v1.8 schema-5 REAL80/MODEL20 fail-closed release policy PASS')

if __name__=='__main__': main()
