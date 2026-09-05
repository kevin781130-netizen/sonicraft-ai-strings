from __future__ import annotations
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'));sys.path.insert(0,str(ROOT/'training'))
from sound_forge import build_forge, forge_row
from string_source_mixer import build_curriculum_weights, mixture_audit
from codec_tournament import run_tournament
from blind_abx import score_responses
from physics_latent_alignment import physics_metric_alignment_loss
from models.string_physics_probe import physics_targets
from release_integrity import verify_release_manifest, IntegrityError

POLICY={'real_probability':.8,'modeled_probability':.2,'modeled_timbre_anchor':False,'modeled_adversarial_target':False,
        'curriculum':'lane_locked_quality_coverage_forge_v19','cleanroom_modeled_only':True}
METRICS={'product':'SONICRAFT AI Strings Q4','release_pass':True,'midi_lock_pass':True,'vibrato_monotonic_pass':True,
         'tempo_transition_pass':True,'dropout_fallback_pass':True,'abx_pass':True,
         'abx':{'generated_identification_accuracy':.55,'target_max_accuracy':.60,'listener_count':3,'trial_count':24}}

def synth(path:Path,freq:float,seed:int):
    sr=48000;t=np.arange(sr,dtype=np.float32)/sr;rng=np.random.default_rng(seed)
    x=.18*np.sin(2*np.pi*freq*t)+.045*np.sin(2*np.pi*2*freq*t)+.012*np.sin(2*np.pi*3*freq*t)
    x += rng.normal(0,0.00025,size=x.shape).astype(np.float32)
    sf.write(path,x,sr,subtype='FLOAT')

def distort(src:Path,dst:Path):
    x,sr=sf.read(src,dtype='float32'); kernel=np.ones(17,dtype=np.float32)/17.0; y=np.convolve(x,kernel,mode='same')*.86
    sf.write(dst,y,sr,subtype='FLOAT')

def must_runtime_reject(md:Path,mutate):
    mp=md/'release_model_manifest.json';m=json.loads(mp.read_text());mutate(m);mp.write_text(json.dumps(m))
    try:verify_release_manifest(md)
    except IntegrityError:return
    raise AssertionError('invalid schema-6 manifest was accepted')

def main():
    with tempfile.TemporaryDirectory() as td0:
        td=Path(td0); audio=td/'audio';audio.mkdir(); reg=json.loads((ROOT/'training/dataset_registry.json').read_text())
        rows=[]
        for i in range(8):
            p=audio/f'real_{i}.wav';synth(p,196+17*i,100+i);rows.append({'audio':str(p),'dataset':'tinysol','training_origin':'real','instrument':i%4,'articulation':i%12})
        for i in range(4):
            p=audio/f'model_{i}.wav';synth(p,220+23*i,200+i);rows.append({'audio':str(p),'dataset':'synthetic_cleanroom_bowed_v18','training_origin':'modeled','instrument':i%4,'articulation':(i+2)%12,
              'bow_speed':.2+.15*i,'bow_force':.3+.1*i,'contact_point':.25+.08*i,'vibrato_depth_cents':8+8*i,'vibrato_rate_hz':4.5+.3*i,'friction_noise':.1+.05*i,
              'spectral_slope':.8+.1*i,'contact_notch_depth':.2+.05*i,'residual_energy':.05+.02*i,'section_pitch_spread_cents':2+2*i,'section_timing_spread_ms':3+2*i,'section_bow_spread':.03+.02*i})
        forged,report=build_forge(rows,reg);assert report['release_pass'] and report['eligible_real_files']==8 and report['eligible_modeled_files']==4
        assert all(r['forge_release_eligible'] for r in forged) and report['training_policy']==POLICY
        # Duplicate audio is detected and removed from training admission.
        dup,_=build_forge(rows+[dict(rows[0])],reg);assert not dup[-1]['forge_release_eligible'] and any('duplicate_audio_of_row' in x for x in dup[-1]['forge_reasons'])
        # Blocked registry material cannot be made legal by row metadata.
        bad=forge_row({'audio':rows[0]['audio'],'dataset':'urmp','release_blocked':False},reg);assert not bad['forge_release_eligible']
        weights=build_curriculum_weights(forged,reg,.8,.2,progress=1.0,require_modeled=True);audit=mixture_audit(forged,weights,reg)
        assert abs(audit['real_probability']-.8)<1e-7 and abs(audit['modeled_probability']-.2)<1e-7

        # Parameter-free physics geometry constraint backpropagates only when enough modeled pairs exist.
        modeled_rows=[r for r in forged if r['training_origin']=='modeled'];target,mask=physics_targets(modeled_rows);z=torch.randn(4,64,7,requires_grad=True)
        pl=physics_metric_alignment_loss(z,target,mask,torch.ones(4,dtype=torch.bool));assert torch.isfinite(pl);pl.backward();assert z.grad is not None

        # Quality-first tournament: exact VAE64 proxy beats a materially degraded 25-Hz challenger.
        pairs=[]
        for i,r in enumerate(rows[:8]):
            ref=Path(r['audio']);good=audio/f'good_{i}.wav';badp=audio/f'bad_{i}.wav';shutil.copy2(ref,good);distort(ref,badp)
            pairs += [
              {'reference':str(ref),'reconstruction':str(good),'candidate_id':'sonicraft_vae64','kind':'strings_vae64','training_origin':'real','latent_ch':64,'latent_hz':30.0,'decoder_bytes':1281137*2},
              {'reference':str(ref),'reconstruction':str(badp),'candidate_id':'ace_25hz_challenger','kind':'ace_oobleck25','training_origin':'real','latent_ch':64,'latent_hz':25.0,'decoder_bytes':9999999},]
        tour=run_tournament(pairs,min_quality=80.0,tie_window=.5);assert tour['promotion_pass'] and tour['winner_kind']=='strings_vae64'
        # If acoustically tied, lower state wins: footprint is a tie-breaker, never a quality override.
        tie=[]
        for i,r in enumerate(rows[:2]):
            ref=r['audio'];tie += [
              {'reference':ref,'reconstruction':ref,'candidate_id':'30hz','kind':'strings_vae64','training_origin':'real','latent_ch':64,'latent_hz':30.0,'decoder_bytes':20},
              {'reference':ref,'reconstruction':ref,'candidate_id':'25hz','kind':'ace_oobleck25','training_origin':'real','latent_ch':64,'latent_hz':25.0,'decoder_bytes':30}]
        assert run_tournament(tie,min_quality=80.0,tie_window=.5)['winner']=='25hz'

        # Deterministic synthetic response set at chance for ABX gate plumbing.
        key={'schema':1,'answers':[{'trial_id':f't{i}','answer':'A' if i%2==0 else 'B'} for i in range(24)]}
        responses=[]
        for i in range(24):
            truth=key['answers'][i]['answer'];guess=truth if i%2==0 else ('B' if truth=='A' else 'A')
            responses.append({'trial_id':f't{i}','answer':guess,'listener_id':f'L{i%3}'})
        codec_abx=score_responses(key,responses,target_max_accuracy=.60);assert codec_abx['transparency_pass'] and codec_abx['listener_count']==3 and codec_abx['trial_count']==24

        # Schema-6 evidence chain and model-pack integrity.
        evidence=td/'evidence';evidence.mkdir();sf_report=evidence/'sound_forge_report.json';ct_report=evidence/'codec_tournament.json';ca_report=evidence/'codec_abx_report.json'
        sf_report.write_text(json.dumps(report));ct_report.write_text(json.dumps(tour));ca_report.write_text(json.dumps(codec_abx))
        prov=evidence/'provenance.json';prov.write_text(json.dumps({'sources':[{'dataset':'tinysol'},{'dataset':'synthetic_cleanroom_bowed_v18'}],'training_policy':POLICY}))
        metrics=evidence/'metrics.json';metrics.write_text(json.dumps(METRICS))
        md=td/'models';md.mkdir()
        for n in ('ballad_renderer_hq_v19_best.pt','ballad_renderer_frontier_v19_shortcut.pt','strings_vae64_decoder_v19.pt'):
            torch.save({'training_mix':{'real':.8,'modeled':.2,'curriculum':POLICY['curriculum']},'model':{}},md/n)
        cmd=[sys.executable,str(ROOT/'training/scripts/build_release_model_manifest.py'),'--model-dir',str(md),'--provenance',str(prov),'--metrics',str(metrics),'--approve','--codec','strings_vae64','--schema','6',
             '--sound-forge-report',str(sf_report),'--codec-tournament',str(ct_report),'--codec-abx-report',str(ca_report)]
        subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL);ok=verify_release_manifest(md);assert ok['verified'] and ok['manifest']['schema']==6
        subprocess.run([sys.executable,str(ROOT/'training/scripts/commercial_release_gate.py'),'--root',str(ROOT),'--model-dir',str(md)],check=True,stdout=subprocess.DEVNULL)
        out=td/'packs';subprocess.run([sys.executable,str(ROOT/'training/scripts/build_profile_model_packs.py'),'--model-dir',str(md),'--out-dir',str(out)],check=True,stdout=subprocess.DEVNULL)
        names={x.name for x in out.glob('*.zip')};assert 'SONICRAFT_AI_Strings_ModelPack_STANDARD_v1.9.0.zip' in names and 'SONICRAFT_AI_Strings_ModelPack_FULL_HQ_v1.9.0.zip' in names

        # Hash-protected evidence means even a one-byte post-approval change fails closed.
        original=(md/'codec_abx_report.json').read_text();(md/'codec_abx_report.json').write_text(original+' ')
        try:verify_release_manifest(md)
        except IntegrityError:pass
        else:raise AssertionError('tampered codec ABX evidence accepted')
    print('v1.9 Sound Forge / codec tournament / physics geometry / schema-6 PASS',
          'forge',report['eligible_real_files'],report['eligible_modeled_files'],'winner',tour['winner'],'abx_acc',codec_abx['accuracy'])

if __name__=='__main__':main()
