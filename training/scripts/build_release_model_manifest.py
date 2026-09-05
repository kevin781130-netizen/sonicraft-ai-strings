from __future__ import annotations
import argparse, hashlib, json, shutil
import torch
from pathlib import Path

PRODUCT='SONICRAFT AI Strings Q4'
VERSION5='1.8.0-frontier-sound-core'
VERSION6='1.9.0-sound-forge'
VERSION7='2.0.0-acoustic-promotion'
POLICY5={
    'real_probability':0.80,'modeled_probability':0.20,
    'modeled_timbre_anchor':False,'modeled_adversarial_target':False,
    'curriculum':'lane_locked_quality_coverage_v18','cleanroom_modeled_only':True,
}
POLICY6={**POLICY5,'curriculum':'lane_locked_quality_coverage_forge_v19'}
POLICY7={**POLICY5,'curriculum':'lane_locked_acoustic_promotion_v20'}


def sha(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()


def normalized_dataset_ids(pj):
    raw=pj.get('datasets') or pj.get('dataset_ids') or pj.get('sources') or []; ids=[]
    for x in raw:
        if isinstance(x,str): k=x
        elif isinstance(x,dict): k=x.get('dataset_id') or x.get('id') or x.get('dataset')
        else: k=None
        if k and k not in ids: ids.append(k)
    return ids


def normalized_training_policy(pj,schema:int):
    p=dict(pj.get('training_policy') or {}); required=POLICY7 if schema>=7 else (POLICY6 if schema>=6 else POLICY5)
    missing=[k for k in required if k not in p]
    if missing: raise SystemExit('training provenance missing policy fields: '+', '.join(missing))
    for k,v in required.items():
        if isinstance(v,float):
            try: ok=abs(float(p[k])-v)<=1e-6
            except Exception: ok=False
        else: ok=(p[k] is v if isinstance(v,bool) else str(p[k])==str(v))
        if not ok: raise SystemExit(f'training_policy mismatch for {k}: expected {v!r}, got {p.get(k)!r}')
    if abs(float(p['real_probability'])+float(p['modeled_probability'])-1.0)>1e-6: raise SystemExit('training_policy probabilities must sum to one')
    return {**p,'real_probability':float(p['real_probability']),'modeled_probability':float(p['modeled_probability'])}


def verify_checkpoint_training_mix(path:Path, role:str, expected_curriculum:str):
    try: ck=torch.load(path,map_location='cpu',weights_only=False)
    except Exception as e: raise SystemExit(f'{role} checkpoint metadata unreadable: {path.name}: {e}') from e
    if not isinstance(ck,dict): raise SystemExit(f'{role} checkpoint must be a metadata dictionary: {path.name}')
    mix=dict(ck.get('training_mix') or {})
    if not mix: raise SystemExit(f'{role} checkpoint missing training_mix: {path.name}')
    try: rp=float(mix.get('real')); mp=float(mix.get('modeled'))
    except Exception as e: raise SystemExit(f'{role} checkpoint has invalid training_mix: {path.name}') from e
    if abs(rp-.80)>1e-6 or abs(mp-.20)>1e-6 or abs(rp+mp-1.0)>1e-6:
        raise SystemExit(f'{role} checkpoint is not REAL80/MODEL20: {path.name} ({rp:.6f}/{mp:.6f})')
    if str(mix.get('curriculum'))!=expected_curriculum:
        raise SystemExit(f'{role} checkpoint has unexpected curriculum: {path.name} ({mix.get("curriculum")!r})')
    return mix


def load_json(path:Path,label:str):
    if not path or not path.is_file(): raise SystemExit(f'{label} evidence file missing')
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:raise SystemExit(f'invalid {label} JSON: {e}') from e


def stage_evidence(md:Path,path:Path,key:str,extra:dict|None=None):
    dst=md/path.name
    if path.resolve()!=dst.resolve(): shutil.copy2(path,dst)
    return {'file':dst.name,'sha256':sha(dst),**(extra or {})}


def validate_sound_forge(report:dict,policy:dict):
    if int(report.get('schema',0))!=1 or report.get('forge_version')!='sound_forge_v19': raise SystemExit('invalid v1.9 Sound Forge report')
    if not report.get('release_pass'): raise SystemExit('Sound Forge report has not passed')
    if int(report.get('eligible_real_files',0))<1 or int(report.get('eligible_modeled_files',0))<1: raise SystemExit('Sound Forge requires eligible real + modeled material')
    if int(report.get('rights_failures',0))!=0 or int(report.get('audio_failures',0))!=0: raise SystemExit('Sound Forge has unresolved rights/audio failures')
    if dict(report.get('training_policy') or {})!=policy: raise SystemExit('Sound Forge training_policy does not match provenance')


def validate_codec_tournament(report:dict,codec_kind:str):
    if int(report.get('schema',0))!=1 or not report.get('promotion_pass'): raise SystemExit('codec tournament has not passed promotion')
    if str(report.get('winner_kind','')).lower()!=str(codec_kind).lower(): raise SystemExit(f'codec tournament winner {report.get("winner_kind")} does not match shipping codec {codec_kind}')
    if int(report.get('real_anchor_count',0))<1: raise SystemExit('codec tournament has no real-anchor evaluation')


def validate_codec_abx(report:dict):
    if int(report.get('schema',0))!=1 or not report.get('transparency_pass'): raise SystemExit('codec ABX transparency has not passed')
    if int(report.get('listener_count',0))<3 or int(report.get('trial_count',0))<20: raise SystemExit('codec ABX requires >=3 listeners and >=20 completed trials')
    acc=report.get('accuracy'); target=float(report.get('target_max_accuracy',.60))
    if acc is None or float(acc)>target: raise SystemExit(f'codec ABX accuracy {acc} exceeds target {target}')


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--model-dir',required=True); ap.add_argument('--provenance',required=True)
    ap.add_argument('--registry',default=str(Path(__file__).resolve().parents[1]/'dataset_registry.json'))
    ap.add_argument('--metrics',required=True); ap.add_argument('--approve',action='store_true')
    ap.add_argument('--codec',choices=('auto','dac44','strings_vae64'),default='auto')
    ap.add_argument('--schema',type=int,choices=(5,6,7),default=6)
    ap.add_argument('--sound-forge-report'); ap.add_argument('--codec-tournament'); ap.add_argument('--codec-abx-report')
    ap.add_argument('--acoustic-segments'); ap.add_argument('--generated-real-abx'); ap.add_argument('--acoustic-promotion')
    a=ap.parse_args(); schema=int(a.schema); md=Path(a.model_dir); prov=Path(a.provenance); metrics=Path(a.metrics); md.mkdir(parents=True,exist_ok=True)
    pj=load_json(prov,'provenance'); reg=load_json(Path(a.registry),'dataset registry'); mj=load_json(metrics,'release metrics')
    used=normalized_dataset_ids(pj); policy=normalized_training_policy(pj,schema)
    if not used: raise SystemExit('training provenance contains no dataset/source IDs')
    blocked=[]
    for k in used:
        e=reg.get(k)
        if not e or e.get('release_blocked') or not e.get('commercial_safe'): blocked.append(k)
    if blocked: raise SystemExit('BLOCKED/UNKNOWN training sources: '+', '.join(sorted(blocked)))
    if mj.get('product') not in (None,PRODUCT): raise SystemExit('release metrics product mismatch')
    if not mj.get('release_pass'): raise SystemExit('release metrics have not passed')
    required=['midi_lock_pass','vibrato_monotonic_pass','tempo_transition_pass','dropout_fallback_pass','abx_pass']
    bad=[k for k in required if not mj.get(k)]
    if bad: raise SystemExit('release metrics missing PASS gates: '+', '.join(bad))
    abx=mj.get('abx') or {}; acc=abx.get('generated_identification_accuracy'); target=float(abx.get('target_max_accuracy',.60))
    if acc is None or float(acc)>target: raise SystemExit(f'ABX identification accuracy {acc} exceeds target {target}')
    if int(abx.get('listener_count',0))<3 or int(abx.get('trial_count',0))<20: raise SystemExit('generated-real ABX requires >=3 listeners and >=20 completed trials')

    staged_prov=md/'training_provenance.json'; staged_metrics=md/'release_metrics.json'
    if prov.resolve()!=staged_prov.resolve(): shutil.copy2(prov,staged_prov)
    if metrics.resolve()!=staged_metrics.resolve(): shutil.copy2(metrics,staged_metrics)
    expected_curriculum=POLICY7['curriculum'] if schema>=7 else (POLICY6['curriculum'] if schema>=6 else POLICY5['curriculum'])
    choices=[
      ('ballad_renderer_hq_v20_best.pt','hq'),('ballad_renderer_hq_v19_best.pt','hq'),('ballad_renderer_hq_v18_best.pt','hq'),('ballad_renderer_hq_best.pt','hq'),('ballad_renderer_best.pt','hq'),('hq_v08_best.pt','hq'),
      ('ballad_renderer_frontier_v20_shortcut.pt','compact'),('ballad_renderer_frontier_v20_distilled.pt','compact'),('ballad_renderer_frontier_v19_shortcut.pt','compact'),('ballad_renderer_frontier_v19_distilled.pt','compact'),('ballad_renderer_frontier_v18_shortcut.pt','compact'),('ballad_renderer_frontier_v18_distilled.pt','compact'),('ballad_renderer_frontier_shortcut.pt','compact'),('frontier_shortcut.pt','compact'),('ballad_renderer_frontier_best.pt','compact'),('ballad_renderer_compact_best.pt','compact'),('compact_v08_distilled.pt','compact'),
      ('strings_vae64_decoder_v20.pt','string_vae64'),('strings_vae64_decoder_v19.pt','string_vae64'),('strings_vae64_decoder_v18.pt','string_vae64'),('strings_vae64_decoder.pt','string_vae64'),
      ('dac_strings_decoder.pt','dac'),('dac_strings_decoder_v04.pt','dac'),('weights_44khz_16kbps.pth','dac_base')]
    out=[];roles=set()
    for name,role in choices:
        p=md/name
        if p.is_file() and role not in roles:
            if role in ('hq','compact','string_vae64'): verify_checkpoint_training_mix(p,role,expected_curriculum)
            out.append({'name':name,'role':role,'sha256':sha(p),'bytes':p.stat().st_size});roles.add(role)
    if not {'hq','compact'}.issubset(roles): raise SystemExit('release requires HQ + Compact/Frontier renderers')
    codec=a.codec
    if codec=='auto':codec='strings_vae64' if 'string_vae64' in roles else 'dac44'
    if codec=='strings_vae64':
        if 'string_vae64' not in roles:raise SystemExit('strings_vae64 release requires decoder checkpoint')
        out=[f for f in out if f['role'] not in ('dac','dac_base')];codec_meta={'kind':'strings_vae64','sample_rate':48000,'latent_ch':64,'latent_hz':30.0,'downsampling_ratio':1600}
    else:
        if not {'dac','dac_base'}.issubset(roles):raise SystemExit('dac44 release requires fine-tuned DAC decoder + base weight')
        out=[f for f in out if f['role']!='string_vae64'];codec_meta={'kind':'dac44','sample_rate':44100,'latent_ch':1024,'latent_hz':25.0}

    evidence={}
    promotion_id=None
    if schema>=6:
        if not (a.sound_forge_report and a.codec_tournament and a.codec_abx_report): raise SystemExit('schema 6+ requires --sound-forge-report --codec-tournament --codec-abx-report')
        sfp=Path(a.sound_forge_report); ctp=Path(a.codec_tournament); cap=Path(a.codec_abx_report)
        sfr=load_json(sfp,'Sound Forge'); ctr=load_json(ctp,'codec tournament'); car=load_json(cap,'codec ABX')
        validate_sound_forge(sfr,policy)
        if schema>=7:
            if int(ctr.get('schema',0))!=2 or not ctr.get('promotion_pass') or str(ctr.get('winner_kind','')).lower()!=codec: raise SystemExit('schema 7 requires v2.0 codec tournament winner to equal shipping codec')
            if int(ctr.get('real_anchor_count',0))<8: raise SystemExit('schema 7 codec tournament requires >=8 real anchors')
            if int(car.get('schema',0))!=2 or not car.get('transparency_pass') or int(car.get('listener_count',0))<5 or int(car.get('trial_count',0))<60 or car.get('significant_above_chance'): raise SystemExit('schema 7 codec ABX failed/underpowered')
        else:
            validate_codec_tournament(ctr,codec);validate_codec_abx(car)
        evidence['sound_forge']=stage_evidence(md,sfp,'sound_forge',{'forge_version':'sound_forge_v19'})
        evidence['codec_tournament']=stage_evidence(md,ctp,'codec_tournament',{'winner':ctr.get('winner'),'winner_kind':ctr.get('winner_kind')})
        evidence['codec_abx']=stage_evidence(md,cap,'codec_abx',{'accuracy':car.get('accuracy'),'target_max_accuracy':car.get('target_max_accuracy')})
    if schema>=7:
        if not (a.acoustic_segments and a.generated_real_abx and a.acoustic_promotion): raise SystemExit('schema 7 requires --acoustic-segments --generated-real-abx --acoustic-promotion')
        sp=Path(a.acoustic_segments);gp=Path(a.generated_real_abx);pp=Path(a.acoustic_promotion)
        sr=load_json(sp,'acoustic segments');gr=load_json(gp,'generated-real ABX');pr=load_json(pp,'acoustic promotion')
        if int(sr.get('schema',0))!=1 or sr.get('segment_version')!='acoustic_segments_v20' or not sr.get('release_pass'): raise SystemExit('invalid acoustic segmentation evidence')
        if int(gr.get('schema',0))!=2 or not gr.get('transparency_pass') or int(gr.get('listener_count',0))<5 or int(gr.get('trial_count',0))<60 or gr.get('significant_above_chance'): raise SystemExit('generated-real ABX failed/underpowered')
        if int(pr.get('schema',0))!=1 or pr.get('promotion_version')!='acoustic_promotion_v20' or not pr.get('promotion_pass'): raise SystemExit('acoustic promotion has not passed')
        if str(pr.get('shipping_codec','')).lower()!=codec or str(pr.get('winner_kind','')).lower()!=codec: raise SystemExit('acoustic promotion winner mismatch')
        promotion_id=str(pr.get('promotion_id',''))
        if len(promotion_id)!=64: raise SystemExit('invalid acoustic promotion ID')
        # Final v2.0 weights must be bound to the exact acoustic promotion evidence.
        for f in out:
            if f['role'] not in ('hq','compact','string_vae64'): continue
            ck=torch.load(md/f['name'],map_location='cpu',weights_only=False); got=str((ck if isinstance(ck,dict) else {}).get('acoustic_promotion_id',''))
            if got!=promotion_id: raise SystemExit(f'{f["role"]} checkpoint acoustic_promotion_id mismatch: {f["name"]}')
            seal=dict((ck if isinstance(ck,dict) else {}).get('acoustic_promotion_seal') or {})
            if int(seal.get('schema',0))!=1 or str(seal.get('promotion_id',''))!=promotion_id or len(str(seal.get('tensor_sha256','')))!=64:
                raise SystemExit(f'{f["role"]} checkpoint missing valid post-ABX promotion seal: {f["name"]}')
        evidence['acoustic_segments']=stage_evidence(md,sp,'acoustic_segments')
        evidence['generated_real_abx']=stage_evidence(md,gp,'generated_real_abx',{'accuracy':gr.get('accuracy')})
        evidence['acoustic_promotion']=stage_evidence(md,pp,'acoustic_promotion',{'promotion_id':promotion_id})

    version=VERSION7 if schema>=7 else (VERSION6 if schema>=6 else VERSION5)
    m={'schema':schema,'product':PRODUCT,'version':version,'profile':'full_hq','commercial_safe':True,'release_approved':bool(a.approve),
       'codec':codec_meta,'sampler':{'family':'shortcut','supported_steps':[1,2,4,8],'recommended_steps':2,'interval_conditioning':True},
       'training_policy':policy,'files':out,'acoustic_promotion_id':promotion_id,
       'provenance':{'file':staged_prov.name,'sha256':sha(staged_prov),'contains_blocked_sources':False,'datasets':sorted(used)},
       'metrics':{'file':staged_metrics.name,'sha256':sha(staged_metrics)},**evidence}
    (md/'release_model_manifest.json').write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding='utf-8')
    print('WROTE',md/'release_model_manifest.json');print('schema:',schema,'codec:',codec,'roles:',sorted({f['role'] for f in out}),'datasets:',sorted(used))

if __name__=='__main__':main()
