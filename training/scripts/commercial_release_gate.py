from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
PRODUCT='SONICRAFT AI Strings Q4'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()

def die(msg): print('RELEASE GATE FAIL:',msg); raise SystemExit(2)

def verify_evidence(md,m,key):
    e=m.get(key) or {}; name=e.get('file'); expected=e.get('sha256')
    if not name or '/' in name or '\\' in name: die(f'{key} evidence filename missing/invalid')
    p=md/name
    if not p.is_file(): die(f'{key} evidence missing: {name}')
    if sha(p)!=str(expected).lower(): die(f'{key} evidence SHA-256 mismatch: {name}')
    return p

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default=str(Path(__file__).resolve().parents[2])); ap.add_argument('--model-dir'); ap.add_argument('--require-binary',action='store_true'); a=ap.parse_args()
    root=Path(a.root); md=Path(a.model_dir) if a.model_dir else root/'Models'
    reg=json.loads((root/'training/dataset_registry.json').read_text(encoding='utf-8'))
    unsafe=[k for k,v in reg.items() if v.get('enabled') and (v.get('release_blocked') or not v.get('commercial_safe'))]
    if unsafe: die('enabled unsafe datasets: '+', '.join(unsafe))
    mp=md/'release_model_manifest.json'
    if not mp.is_file(): die('release_model_manifest.json missing')
    m=json.loads(mp.read_text(encoding='utf-8'))
    if int(m.get('schema',0)) not in (1,2,3,4,5,6,7) or m.get('product')!=PRODUCT: die('model manifest schema/product mismatch')
    if not m.get('commercial_safe') or not m.get('release_approved'): die('model manifest is not commercial-safe + approved')
    if (m.get('provenance') or {}).get('contains_blocked_sources'): die('model provenance reports blocked sources')
    roles=set()
    for f in m.get('files',[]):
        name=f.get('name',''); p=md/name; roles.add(f.get('role'))
        if not name or '/' in name or '\\' in name: die('invalid model filename')
        if not p.is_file(): die('model missing: '+name)
        if sha(p)!=str(f.get('sha256','')).lower(): die('model hash mismatch: '+name)
    if 'hq' not in roles: die('HQ renderer role required')
    kind=str((m.get('codec') or {}).get('kind','dac44')).lower()
    if kind=='strings_vae64':
        if 'string_vae64' not in roles: die('strings_vae64 decoder role required')
    elif not {'dac','dac_base'}.issubset(roles): die('DAC fine-tune + DAC base roles required')
    prov_path=verify_evidence(md,m,'provenance'); metrics_path=verify_evidence(md,m,'metrics')
    prov=json.loads(prov_path.read_text(encoding='utf-8')); used=prov.get('datasets') or prov.get('dataset_ids') or prov.get('sources') or []
    used_ids=[]
    for x in used:
        k=x if isinstance(x,str) else (x.get('dataset_id') or x.get('id') or x.get('dataset') if isinstance(x,dict) else None)
        if k: used_ids.append(k)
    if not used_ids: die('training provenance has no source IDs')
    for k in used_ids:
        v=reg.get(k)
        if not v or v.get('release_blocked') or not v.get('commercial_safe'): die('provenance uses blocked/unknown source: '+str(k))
    if int(m.get('schema',0))>=5:
        policy=dict(m.get('training_policy') or {}); pp=dict(prov.get('training_policy') or {})
        if policy != pp: die('manifest/provenance training_policy mismatch')
        required=('real_probability','modeled_probability','modeled_timbre_anchor','modeled_adversarial_target','curriculum','cleanroom_modeled_only')
        if any(k not in policy for k in required): die('schema 5 training_policy incomplete')
        try: rp=float(policy['real_probability']); mp=float(policy['modeled_probability'])
        except Exception: die('invalid training_policy probabilities')
        if abs(rp-.80)>1e-6 or abs(mp-.20)>1e-6 or abs(rp+mp-1.0)>1e-6: die('v1.8 release requires REAL80/MODEL20')
        if policy['modeled_timbre_anchor'] is not False: die('modeled timbre anchor forbidden')
        if policy['modeled_adversarial_target'] is not False: die('modeled adversarial target forbidden')
        if policy['cleanroom_modeled_only'] is not True: die('clean-room material must remain modeled-only')
        expected='lane_locked_acoustic_promotion_v20' if int(m.get('schema',0))>=7 else ('lane_locked_quality_coverage_forge_v19' if int(m.get('schema',0))>=6 else 'lane_locked_quality_coverage_v18')
        if str(policy['curriculum'])!=expected: die('unexpected training curriculum')

    if int(m.get('schema',0))>=6:
        sf_path=verify_evidence(md,m,'sound_forge'); ct_path=verify_evidence(md,m,'codec_tournament'); ca_path=verify_evidence(md,m,'codec_abx')
        sf=json.loads(sf_path.read_text(encoding='utf-8')); ct=json.loads(ct_path.read_text(encoding='utf-8')); ca=json.loads(ca_path.read_text(encoding='utf-8'))
        if int(sf.get('schema',0))!=1 or sf.get('forge_version')!='sound_forge_v19' or not sf.get('release_pass'): die('Sound Forge evidence failed')
        if int(sf.get('eligible_real_files',0))<1 or int(sf.get('eligible_modeled_files',0))<1: die('Sound Forge lacks eligible real/modeled material')
        if int(sf.get('rights_failures',0)) or int(sf.get('audio_failures',0)): die('Sound Forge unresolved rights/audio failures')
        if dict(sf.get('training_policy') or {})!=dict(m.get('training_policy') or {}): die('Sound Forge/manifest policy mismatch')
        if int(m.get('schema',0))>=7:
            if int(ct.get('schema',0))!=2 or str(ct.get('metric_family',''))!='stereo_phase_harmonic_strings_v20' or not ct.get('promotion_pass'): die('v2.0 codec tournament failed')
            if int(ct.get('real_anchor_count',0))<8: die('v2.0 codec tournament requires >=8 real anchors')
            if int(ca.get('schema',0))!=2 or not ca.get('transparency_pass'): die('v2.0 codec ABX transparency failed')
            if int(ca.get('listener_count',0))<5 or int(ca.get('trial_count',0))<60 or ca.get('significant_above_chance'): die('v2.0 codec ABX underpowered/significantly identifiable')
        else:
            if int(ct.get('schema',0))!=1 or not ct.get('promotion_pass'): die('codec tournament failed')
            if int(ca.get('schema',0))!=1 or not ca.get('transparency_pass'): die('codec ABX transparency failed')
            if int(ca.get('listener_count',0))<3 or int(ca.get('trial_count',0))<20: die('codec ABX requires >=3 listeners and >=20 trials')
        if str(ct.get('winner_kind','')).lower()!=kind: die('shipping codec did not win codec tournament')
        ca_acc=ca.get('accuracy'); ca_target=float(ca.get('target_max_accuracy',.60))
        if ca_acc is None or float(ca_acc)>ca_target: die('codec ABX identification exceeds target')

    if int(m.get('schema',0))>=7:
        seg_path=verify_evidence(md,m,'acoustic_segments'); gr_path=verify_evidence(md,m,'generated_real_abx'); ap_path=verify_evidence(md,m,'acoustic_promotion')
        seg=json.loads(seg_path.read_text(encoding='utf-8')); gr=json.loads(gr_path.read_text(encoding='utf-8')); apr=json.loads(ap_path.read_text(encoding='utf-8'))
        if int(seg.get('schema',0))!=1 or seg.get('segment_version')!='acoustic_segments_v20' or not seg.get('release_pass'): die('v2.0 acoustic segmentation failed')
        if int(seg.get('real_segments',0))<1 or int(seg.get('modeled_segments',0))<1: die('v2.0 segmentation lacks both lanes')
        if int(gr.get('schema',0))!=2 or not gr.get('transparency_pass') or int(gr.get('listener_count',0))<5 or int(gr.get('trial_count',0))<60 or gr.get('significant_above_chance'): die('generated-real ABX failed/underpowered')
        if int(apr.get('schema',0))!=1 or apr.get('promotion_version')!='acoustic_promotion_v20' or not apr.get('promotion_pass'): die('acoustic promotion contract failed')
        if str(apr.get('shipping_codec','')).lower()!=kind or str(apr.get('winner_kind','')).lower()!=kind: die('acoustic promotion codec mismatch')
        if str(m.get('acoustic_promotion_id',''))!=str(apr.get('promotion_id','')): die('acoustic promotion identity mismatch')

    mj=json.loads(metrics_path.read_text(encoding='utf-8'))
    if not mj.get('release_pass'): die('release metrics fail')
    required=['midi_lock_pass','vibrato_monotonic_pass','tempo_transition_pass','dropout_fallback_pass','abx_pass']
    for k in required:
        if not mj.get(k): die('metric gate failed: '+k)
    abx=mj.get('abx') or {}; acc=abx.get('generated_identification_accuracy'); target=float(abx.get('target_max_accuracy',.60))
    if acc is None or float(acc)>target: die(f'ABX identification accuracy {acc} exceeds target {target}')
    if int(abx.get('listener_count',0))<3 or int(abx.get('trial_count',0))<20: die('ABX requires >=3 listeners and >=20 completed trials')
    if a.require_binary:
        vst=root/'release/SONICRAFT AI Strings Q4.vst3'
        if not vst.exists(): die('prebuilt VST3 bundle missing')
    print('COMMERCIAL RELEASE GATE PASS')
if __name__=='__main__': main()
