from __future__ import annotations
import json,shutil,subprocess,sys,tempfile
from pathlib import Path
import numpy as np,soundfile as sf,torch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runtime'));sys.path.insert(0,str(ROOT/'training'))
from sound_forge import build_forge
from acoustic_segmentation import segment_forged_rows
from codec_tournament_v20 import run_tournament_v20
from blind_abx_v20 import score_abx_v20
from acoustic_promotion import build_promotion
from release_integrity import verify_release_manifest,IntegrityError

POLICY={'real_probability':.8,'modeled_probability':.2,'modeled_timbre_anchor':False,'modeled_adversarial_target':False,
        'curriculum':'lane_locked_acoustic_promotion_v20','cleanroom_modeled_only':True}
METRICS={'product':'SONICRAFT AI Strings Q4','release_pass':True,'midi_lock_pass':True,'vibrato_monotonic_pass':True,
         'tempo_transition_pass':True,'dropout_fallback_pass':True,'abx_pass':True,
         'abx':{'generated_identification_accuracy':.50,'target_max_accuracy':.60,'listener_count':5,'trial_count':100}}

def synth(path:Path,freq:float,seed:int,dur=2.0):
    sr=48000;t=np.arange(int(sr*dur),dtype=np.float32)/sr;r=np.random.default_rng(seed)
    env=np.minimum(1,t/.035)*np.minimum(1,(dur-t)/.08);vib=np.sin(2*np.pi*5.2*t)*.003
    ph=2*np.pi*freq*(t+vib/freq)
    l=(.17*np.sin(ph)+.050*np.sin(2*ph+.1)+.018*np.sin(3*ph+.3)+r.normal(0,.00035,len(t)))*env
    rr=(.16*np.sin(ph+.018)+.048*np.sin(2*ph+.16)+.016*np.sin(3*ph+.38)+r.normal(0,.00035,len(t)))*env
    sf.write(path,np.stack([l,rr],1).astype(np.float32),sr,subtype='FLOAT')

def degrade(src:Path,dst:Path):
    x,sr=sf.read(src,dtype='float32',always_2d=True);k=np.ones(25,dtype=np.float32)/25
    l=np.convolve(x[:,0],k,mode='same')*.86; # collapse width + smear transient/phase
    y=np.stack([l,l],1);sf.write(dst,y,sr,subtype='FLOAT')

def chance_report(prefix='t'):
    answers=[];responses=[]
    for i in range(100):
        truth='A' if i%2==0 else 'B';answers.append({'trial_id':f'{prefix}{i}','answer':truth,'trial_kind':'target'})
        lid=f'L{i//20}';guess=truth if i%2==0 else ('B' if truth=='A' else 'A')
        responses.append({'trial_id':f'{prefix}{i}','answer':guess,'listener_id':lid})
    return score_abx_v20({'schema':2,'answers':answers},responses,target_max_accuracy=.60,min_listeners=5,min_total_trials=60)

def main():
  with tempfile.TemporaryDirectory() as td0:
    td=Path(td0);audio=td/'audio';audio.mkdir();reg=json.loads((ROOT/'training/dataset_registry.json').read_text())
    rows=[]
    for i in range(8):
        p=audio/f'real_{i}.wav';synth(p,170+19*i,100+i);rows.append({'audio':str(p),'dataset':'tinysol','training_origin':'real','instrument':i%4,'articulation':i%12})
    for i in range(4):
        p=audio/f'modeled_{i}.wav';synth(p,205+23*i,200+i);rows.append({'audio':str(p),'dataset':'synthetic_cleanroom_bowed_v18','training_origin':'modeled','instrument':i%4,'articulation':(i+3)%12})
    forged,sf_report=build_forge(rows,reg,curriculum=POLICY['curriculum']);assert sf_report['release_pass'] and sf_report['training_policy']==POLICY
    segs,seg_report=segment_forged_rows(forged,td/'segments');assert seg_report['release_pass'] and seg_report['real_segments']==8 and seg_report['modeled_segments']==4
    pairs=[]
    for i,r in enumerate(rows[:8]):
        ref=Path(r['audio']);good=audio/f'good_{i}.wav';bad=audio/f'bad_{i}.wav';shutil.copy2(ref,good);degrade(ref,bad)
        pairs += [
          {'reference':str(ref),'reconstruction':str(good),'candidate_id':'sonicraft_vae64','kind':'strings_vae64','training_origin':'real','latent_ch':64,'latent_hz':30.0,'decoder_bytes':1281137*2},
          {'reference':str(ref),'reconstruction':str(bad),'candidate_id':'ace25','kind':'ace_oobleck25','training_origin':'real','latent_ch':64,'latent_hz':25.0,'decoder_bytes':1000000}]
    tour=run_tournament_v20(pairs,min_quality=82,tie_window=.4,min_real_anchors=8);assert tour['promotion_pass'] and tour['winner_kind']=='strings_vae64' and tour['real_anchor_count']==8
    codec_abx=chance_report('c');gen_abx=chance_report('g');assert codec_abx['transparency_pass'] and gen_abx['transparency_pass'] and codec_abx['listener_count']==5 and codec_abx['trial_count']==100
    promotion=build_promotion(sf_report,seg_report,tour,codec_abx,gen_abx,shipping_codec='strings_vae64');assert promotion['promotion_pass'] and len(promotion['promotion_id'])==64
    # A winning research codec without audited runtime adapter blocks release rather than silently shipping an incompatible decoder.
    blocked=dict(tour);blocked['winner_kind']='ace_oobleck25';bp=build_promotion(sf_report,seg_report,blocked,codec_abx,gen_abx,shipping_codec='ace_oobleck25');assert not bp['promotion_pass'] and 'winner_has_no_audited_runtime_adapter' in bp['reasons']

    evidence=td/'evidence';evidence.mkdir()
    def dump(name,obj):p=evidence/name;p.write_text(json.dumps(obj,indent=2));return p
    sfp=dump('sound_forge_report.json',sf_report);sgp=dump('acoustic_segments_report.json',seg_report);ctp=dump('codec_tournament_v20.json',tour);cap=dump('codec_abx_report.json',codec_abx);gap=dump('generated_real_abx_report.json',gen_abx);app=dump('acoustic_promotion.json',promotion)
    prov=dump('provenance.json',{'sources':[{'dataset':'tinysol'},{'dataset':'synthetic_cleanroom_bowed_v18'}],'training_policy':POLICY});metrics=dump('metrics.json',METRICS)
    md=td/'models';md.mkdir();mix={'real':.8,'modeled':.2,'curriculum':POLICY['curriculum']};pid=promotion['promotion_id']
    for n in ('ballad_renderer_hq_v20_best.pt','ballad_renderer_frontier_v20_shortcut.pt','strings_vae64_decoder_v20.pt'):
        torch.save({'training_mix':mix,'acoustic_promotion_id':None,'model':{'w':torch.randn(2,3)}},md/n)
        subprocess.run([sys.executable,str(ROOT/'training/scripts/seal_checkpoint_promotion.py'),'--checkpoint',str(md/n),'--promotion',str(app)],check=True,stdout=subprocess.DEVNULL)
    cmd=[sys.executable,str(ROOT/'training/scripts/build_release_model_manifest.py'),'--model-dir',str(md),'--provenance',str(prov),'--metrics',str(metrics),'--approve','--codec','strings_vae64','--schema','7',
         '--sound-forge-report',str(sfp),'--codec-tournament',str(ctp),'--codec-abx-report',str(cap),'--acoustic-segments',str(sgp),'--generated-real-abx',str(gap),'--acoustic-promotion',str(app)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL);ok=verify_release_manifest(md);assert ok['verified'] and ok['manifest']['schema']==7 and ok['manifest']['acoustic_promotion_id']==pid
    subprocess.run([sys.executable,str(ROOT/'training/scripts/commercial_release_gate.py'),'--root',str(ROOT),'--model-dir',str(md)],check=True,stdout=subprocess.DEVNULL)
    out=td/'packs';subprocess.run([sys.executable,str(ROOT/'training/scripts/build_profile_model_packs.py'),'--model-dir',str(md),'--out-dir',str(out)],check=True,stdout=subprocess.DEVNULL)
    names={x.name for x in out.glob('*.zip')};assert 'SONICRAFT_AI_Strings_ModelPack_STANDARD_v2.0.0.zip' in names and 'SONICRAFT_AI_Strings_ModelPack_FULL_HQ_v2.0.0.zip' in names
    # Evidence and model binding are both fail-closed.
    original=(md/'acoustic_promotion.json').read_text();(md/'acoustic_promotion.json').write_text(original+' ')
    try:verify_release_manifest(md)
    except IntegrityError:pass
    else:raise AssertionError('tampered acoustic promotion evidence accepted')
  print('v2.0 acoustic segmentation / stereo-phase codec / robust ABX / schema-7 promotion PASS',
        'winner',tour['winner'],'quality',round(tour['winner_quality'],3),'abx',codec_abx['accuracy'],'promotion',promotion['promotion_id'][:12])

if __name__=='__main__':main()
