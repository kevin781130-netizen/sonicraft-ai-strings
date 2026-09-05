from __future__ import annotations
import argparse, json, hashlib, shutil, zipfile, re
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()

def version_tag(full:dict)->str:
    v=str(full.get('version','1.0.0')); m=re.match(r'(\d+\.\d+\.\d+)',v)
    return m.group(1) if m else v.replace('/','-')

def build(md:Path,out:Path,profile:str,roles:set[str],zip_name:str):
    full=json.loads((md/'release_model_manifest.json').read_text(encoding='utf-8'))
    if not full.get('commercial_safe') or not full.get('release_approved'): raise SystemExit('full manifest is not approved')
    files=[f for f in full.get('files',[]) if f.get('role') in roles];have={f.get('role') for f in files};missing=roles-have
    if missing:raise SystemExit(f'{profile}: missing roles {sorted(missing)}')
    stage=out/profile;shutil.rmtree(stage,ignore_errors=True);stage.mkdir(parents=True)
    for f in files:shutil.copy2(md/f['name'],stage/f['name'])
    for key in ('provenance','metrics','sound_forge','codec_tournament','codec_abx','acoustic_segments','generated_real_abx','acoustic_promotion'):
        e=full.get(key)
        if e:shutil.copy2(md/e['file'],stage/e['file'])
    m=dict(full);m['profile']=profile;m['files']=files
    (stage/'release_model_manifest.json').write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding='utf-8')
    zp=out/zip_name
    if zp.exists():zp.unlink()
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(stage.iterdir()):z.write(p,p.name)
    return {'profile':profile,'zip':zp.name,'bytes':zp.stat().st_size,'sha256':sha(zp),'roles':sorted(have)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model-dir',required=True);ap.add_argument('--out-dir',required=True);a=ap.parse_args()
    md=Path(a.model_dir);out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);full=json.loads((md/'release_model_manifest.json').read_text())
    kind=str((full.get('codec') or {}).get('kind','dac44')).lower();codec_roles={'string_vae64'} if kind=='strings_vae64' else {'dac','dac_base'};v=version_tag(full)
    items=[build(md,out,'standard',{'compact'}|codec_roles,f'SONICRAFT_AI_Strings_ModelPack_STANDARD_v{v}.zip'),
           build(md,out,'full_hq',{'compact','hq'}|codec_roles,f'SONICRAFT_AI_Strings_ModelPack_FULL_HQ_v{v}.zip')]
    (out/'model_pack_hashes.json').write_text(json.dumps(items,indent=2),encoding='utf-8');print(json.dumps(items,indent=2))
if __name__=='__main__':main()
