from __future__ import annotations
import hashlib, json
from pathlib import Path

PRODUCT = "SONICRAFT AI Strings Q4"
SUPPORTED_MANIFEST_SCHEMAS = {1,2,3,4,5,6,7}

class IntegrityError(RuntimeError): pass

def sha256_file(path: Path, chunk=4*1024*1024) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        while True:
            b=f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()

def verify_release_manifest(model_dir: Path, allow_dev: bool=False):
    model_dir=Path(model_dir); mp=model_dir/'release_model_manifest.json'
    if not mp.exists():
        if allow_dev: return {"verified":False,"dev_override":True,"detail":"manifest missing; developer override"}
        raise IntegrityError('release_model_manifest.json is required for AUTO/HQ release weights')
    try: m=json.loads(mp.read_text(encoding='utf-8'))
    except Exception as e: raise IntegrityError(f'invalid release model manifest: {e}') from e
    schema=int(m.get('schema',0))
    if schema not in SUPPORTED_MANIFEST_SCHEMAS: raise IntegrityError('unsupported release model manifest schema')
    if m.get('product')!=PRODUCT: raise IntegrityError('model package product mismatch')
    if not bool(m.get('commercial_safe')): raise IntegrityError('model package is not marked commercial_safe')
    if not bool(m.get('release_approved')): raise IntegrityError('model package has not passed release approval')
    prov=m.get('provenance',{})
    if not prov.get('sha256'): raise IntegrityError('training provenance SHA-256 missing')
    if prov.get('contains_blocked_sources'): raise IntegrityError('training provenance reports blocked/non-commercial sources')
    files=m.get('files') or []; roles=set()
    if not files: raise IntegrityError('model package contains no files')
    for f in files:
        name=f.get('name'); expected=str(f.get('sha256','')).lower(); role=f.get('role')
        if not name or '/' in name or '\\' in name: raise IntegrityError('invalid model filename in manifest')
        if role: roles.add(role)
        p=model_dir/name
        if not p.is_file(): raise IntegrityError(f'model file missing: {name}')
        if len(expected)!=64: raise IntegrityError(f'invalid SHA-256 for {name}')
        if sha256_file(p).lower()!=expected: raise IntegrityError(f'model SHA-256 mismatch: {name}')

    if not ({'compact','hq'} & roles): raise IntegrityError('model package needs at least one renderer role: compact or hq')
    codec=dict(m.get('codec') or {})
    codec_kind=str(codec.get('kind','dac44')).lower()
    if codec_kind=='strings_vae64':
        if 'string_vae64' not in roles: raise IntegrityError('strings_vae64 profile requires string_vae64 decoder role')
        if schema>=3:
            if int(codec.get('latent_ch',0))!=64: raise IntegrityError('strings_vae64 manifest latent_ch must be 64')
            if float(codec.get('latent_hz',0))<=0 or int(codec.get('sample_rate',0))<=0: raise IntegrityError('invalid strings_vae64 codec geometry')
    else:
        missing={'dac_base','dac'}-roles
        if missing: raise IntegrityError(f'missing required DAC model roles: {sorted(missing)}')
        codec_kind='dac44'

    if schema>=4:
        sampler=dict(m.get('sampler') or {})
        family=str(sampler.get('family','rectified_flow')).lower()
        if family not in ('rectified_flow','shortcut'):
            raise IntegrityError('unsupported sampler family')
        if family=='shortcut':
            steps=sampler.get('supported_steps') or []
            if not steps or any(int(x)<1 for x in steps): raise IntegrityError('shortcut sampler requires positive supported_steps')
            rec=int(sampler.get('recommended_steps',0))
            if rec not in [int(x) for x in steps]: raise IntegrityError('shortcut recommended_steps must be supported')
            if not bool(sampler.get('interval_conditioning')): raise IntegrityError('shortcut manifest requires interval_conditioning')

    if schema>=5:
        policy=dict(m.get('training_policy') or {})
        required=('real_probability','modeled_probability','modeled_timbre_anchor','modeled_adversarial_target','curriculum','cleanroom_modeled_only')
        if any(k not in policy for k in required): raise IntegrityError('schema 5 requires complete training_policy')
        try: rp=float(policy['real_probability']); mp=float(policy['modeled_probability'])
        except Exception as e: raise IntegrityError('invalid training_policy probabilities') from e
        if abs(rp-.80)>1e-6 or abs(mp-.20)>1e-6 or abs(rp+mp-1.0)>1e-6:
            raise IntegrityError('schema 5 requires REAL80/MODEL20 probability mass')
        if policy['modeled_timbre_anchor'] is not False: raise IntegrityError('modeled data cannot be final timbre anchor')
        if policy['modeled_adversarial_target'] is not False: raise IntegrityError('modeled data cannot be adversarial real target')
        if policy['cleanroom_modeled_only'] is not True: raise IntegrityError('clean-room material must remain modeled-only')
        expected_curriculum='lane_locked_acoustic_promotion_v20' if schema>=7 else ('lane_locked_quality_coverage_forge_v19' if schema>=6 else 'lane_locked_quality_coverage_v18')
        if str(policy['curriculum'])!=expected_curriculum: raise IntegrityError(f'unexpected training curriculum: {policy["curriculum"]}')

    if schema>=6:
        evidence_json={}
        for label in ('sound_forge','codec_tournament','codec_abx'):
            e=m.get(label) or {}; name=e.get('file'); expected=str(e.get('sha256','')).lower()
            if not name or '/' in name or '\\' in name: raise IntegrityError(f'{label} evidence filename missing/invalid')
            p=model_dir/name
            if not p.is_file(): raise IntegrityError(f'{label} evidence missing: {name}')
            if len(expected)!=64 or sha256_file(p).lower()!=expected: raise IntegrityError(f'{label} evidence SHA-256 mismatch: {name}')
            try: evidence_json[label]=json.loads(p.read_text(encoding='utf-8'))
            except Exception as ex: raise IntegrityError(f'invalid {label} evidence JSON: {ex}') from ex
        sf=evidence_json['sound_forge']; ct=evidence_json['codec_tournament']; ca=evidence_json['codec_abx']
        if int(sf.get('schema',0))!=1 or sf.get('forge_version')!='sound_forge_v19' or not sf.get('release_pass'): raise IntegrityError('Sound Forge evidence has not passed')
        if int(sf.get('eligible_real_files',0))<1 or int(sf.get('eligible_modeled_files',0))<1: raise IntegrityError('Sound Forge evidence lacks real/modeled material')
        if int(sf.get('rights_failures',0)) or int(sf.get('audio_failures',0)): raise IntegrityError('Sound Forge evidence reports unresolved failures')
        if dict(sf.get('training_policy') or {})!=policy: raise IntegrityError('Sound Forge/manifest training_policy mismatch')
        if not ct.get('promotion_pass'): raise IntegrityError('codec tournament has not passed')
        if str(ct.get('winner_kind','')).lower()!=codec_kind: raise IntegrityError('codec tournament winner does not match shipping codec')
        if int(ct.get('real_anchor_count',0))<1: raise IntegrityError('codec tournament lacks real anchors')
        if schema>=7:
            if int(ct.get('schema',0))!=2 or str(ct.get('metric_family',''))!='stereo_phase_harmonic_strings_v20': raise IntegrityError('schema 7 requires v2.0 stereo/phase/harmonic codec tournament')
            if int(ca.get('schema',0))!=2 or not ca.get('transparency_pass'): raise IntegrityError('schema 7 codec ABX has not passed')
            if int(ca.get('listener_count',0))<5 or int(ca.get('trial_count',0))<60: raise IntegrityError('schema 7 codec ABX requires >=5 listeners and >=60 target trials')
            if ca.get('significant_above_chance'): raise IntegrityError('codec ABX is significantly identifiable above chance')
        else:
            if int(ca.get('schema',0))!=1 or not ca.get('transparency_pass'): raise IntegrityError('codec ABX has not passed')
            if int(ca.get('listener_count',0))<3 or int(ca.get('trial_count',0))<20: raise IntegrityError('codec ABX requires >=3 listeners and >=20 trials')
        acc=ca.get('accuracy'); target=float(ca.get('target_max_accuracy',.60))
        if acc is None or float(acc)>target: raise IntegrityError('codec ABX exceeds identification target')

    if schema>=7:
        evidence_json={}
        for label in ('acoustic_segments','generated_real_abx','acoustic_promotion'):
            e=m.get(label) or {}; name=e.get('file'); expected=str(e.get('sha256','')).lower()
            if not name or '/' in name or '\\' in name: raise IntegrityError(f'{label} evidence filename missing/invalid')
            p=model_dir/name
            if not p.is_file(): raise IntegrityError(f'{label} evidence missing: {name}')
            if len(expected)!=64 or sha256_file(p).lower()!=expected: raise IntegrityError(f'{label} evidence SHA-256 mismatch: {name}')
            try: evidence_json[label]=json.loads(p.read_text(encoding='utf-8'))
            except Exception as ex: raise IntegrityError(f'invalid {label} evidence JSON: {ex}') from ex
        seg=evidence_json['acoustic_segments']; ga=evidence_json['generated_real_abx']; ap=evidence_json['acoustic_promotion']
        if int(seg.get('schema',0))!=1 or seg.get('segment_version')!='acoustic_segments_v20' or not seg.get('release_pass'): raise IntegrityError('v2.0 acoustic segmentation has not passed')
        if int(seg.get('real_segments',0))<1 or int(seg.get('modeled_segments',0))<1: raise IntegrityError('v2.0 segmentation lacks both lanes')
        if int(ga.get('schema',0))!=2 or not ga.get('transparency_pass'): raise IntegrityError('generated-real ABX has not passed')
        if int(ga.get('listener_count',0))<5 or int(ga.get('trial_count',0))<60 or ga.get('significant_above_chance'): raise IntegrityError('generated-real ABX underpowered or significantly identifiable')
        if int(ap.get('schema',0))!=1 or ap.get('promotion_version')!='acoustic_promotion_v20' or not ap.get('promotion_pass'): raise IntegrityError('acoustic promotion contract has not passed')
        if str(ap.get('shipping_codec','')).lower()!=codec_kind or str(ap.get('winner_kind','')).lower()!=codec_kind: raise IntegrityError('acoustic promotion winner/shipping codec mismatch')
        pid=str(ap.get('promotion_id',''))
        if len(pid)!=64 or str(m.get('acoustic_promotion_id',''))!=pid: raise IntegrityError('acoustic promotion identity mismatch')

    profile=str(m.get('profile','full_hq')).lower()
    if profile=='standard' and 'compact' not in roles: raise IntegrityError('standard profile requires compact renderer')
    if profile in ('full_hq','hq','full') and 'hq' not in roles: raise IntegrityError('full HQ profile requires hq renderer')
    m['_capabilities']={'auto':('compact' in roles or 'hq' in roles),'hq':('hq' in roles),'compact':('compact' in roles),'codec':codec_kind}
    for label in ('provenance','metrics'):
        e=m.get(label) or {}; name=e.get('file'); expected=str(e.get('sha256','')).lower()
        if not name or '/' in name or '\\' in name: raise IntegrityError(f'{label} evidence filename missing/invalid')
        p=model_dir/name
        if not p.is_file(): raise IntegrityError(f'{label} evidence missing: {name}')
        if len(expected)!=64 or sha256_file(p).lower()!=expected: raise IntegrityError(f'{label} evidence SHA-256 mismatch: {name}')
    return {"verified":True,"manifest":m,"detail":f'verified {len(files)} model files + release evidence ({codec_kind})'}
