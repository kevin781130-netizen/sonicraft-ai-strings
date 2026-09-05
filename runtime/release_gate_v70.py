from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

RELEASE='7.0.0-rc2'

def sha256(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def load_json(path: Path, failures: list[str], label: str):
    if not path.is_file():
        failures.append(f'missing {path.name}')
        return None
    try: return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception as e:
        failures.append(f'invalid {label}: {e}')
        return None

def locate_vst3_binary(root: Path) -> Path|None:
    bundle=root/'release'/'SONICRAFT AI Strings Q4.vst3'/'Contents'/'x86_64-win'
    if not bundle.is_dir(): return None
    return next(iter(sorted(bundle.glob('*.vst3'))),None)

def verify_model_pack(root: Path, failures: list[str], evidence: dict) -> str|None:
    model_root=root/'release'/'prebuilt'/'Models'
    mp=model_root/'release_model_manifest.json'
    m=load_json(mp,failures,'model manifest')
    if not m: return None
    manifest_sha=sha256(mp).lower()
    evidence['model_manifest_sha256']=manifest_sha
    approved=bool(m.get('commercial_safe')) and bool(m.get('release_approved'))
    evidence['model_approved']=approved
    if not approved: failures.append('model manifest is not commercial_safe + release_approved')
    files=m.get('files',[])
    if not files: failures.append('model manifest has no model files')
    for item in files:
        name=item.get('name'); expected=str(item.get('sha256','')).lower()
        if not name or not expected:
            failures.append('model manifest contains file entry without name/sha256');continue
        p=model_root/name
        if not p.is_file(): failures.append(f'model missing: {name}');continue
        actual=sha256(p).lower()
        if actual!=expected: failures.append(f'model hash mismatch: {name}')
    return manifest_sha

def evaluate(root: Path, public: bool=False) -> tuple[int,dict]:
    ev=root/'release'/'rc_evidence';ev.mkdir(parents=True,exist_ok=True)
    failures=[];evidence={}
    build=load_json(ev/'build-provenance.json',failures,'build provenance')
    val=load_json(ev/'validator-pass.json',failures,'validator evidence')
    cubase=load_json(ev/'host-qa-cubase.json',failures,'Cubase evidence')
    studio=load_json(ev/'host-qa-studio-one.json',failures,'Studio One evidence')
    acoustic=load_json(ev/'acoustic-qa.json',failures,'acoustic evidence')
    for label,obj in [('build provenance',build),('validator evidence',val),('Cubase evidence',cubase),('Studio One evidence',studio),('acoustic evidence',acoustic)]:
        if obj and obj.get('release')!=RELEASE:
            failures.append(f'{label} belongs to release {obj.get("release")!r}, expected {RELEASE}')
    expected_sdk='9fad9770f2ae8542ab1a548a68c1ad1ac690abe0'
    if build:
        evidence['build']=build.get('status')
        if build.get('status')!='PASS': failures.append('build-provenance not PASS')
        sdk=(build.get('vst3_sdk') or {})
        if str(sdk.get('version',''))!='3.8.0' or str(sdk.get('commit','')).lower()!=expected_sdk:
            failures.append('build provenance is not bound to pinned VST3 SDK 3.8.0 commit')
    if val:
        evidence['validator']=val.get('passed')
        if val.get('passed') is not True: failures.append('Steinberg Validator not PASS')
        if str(val.get('vst3_sdk_version',''))!='3.8.0' or str(val.get('vst3_sdk_commit','')).lower()!=expected_sdk:
            failures.append('validator evidence is not from pinned VST3 SDK 3.8.0 commit')
    if cubase:
        evidence['cubase']=cubase.get('overall')
        if cubase.get('overall')!='PASS': failures.append('Cubase QA not PASS')
        if not cubase.get('host_exe') or cubase.get('host_version') in (None,'','unknown'):
            failures.append('Cubase QA lacks a concrete detected/selected host executable and version')
        if len(str(cubase.get('host_exe_sha256','')))!=64:
            failures.append('Cubase QA lacks host executable SHA-256 provenance')
    if studio:
        evidence['studio_one']=studio.get('overall')
        if studio.get('overall')!='PASS': failures.append('Studio One QA not PASS')
        if not studio.get('host_exe') or studio.get('host_version') in (None,'','unknown'):
            failures.append('Studio One QA lacks a concrete detected/selected host executable and version')
        if len(str(studio.get('host_exe_sha256','')))!=64:
            failures.append('Studio One QA lacks host executable SHA-256 provenance')
    if acoustic:
        evidence['acoustic']=acoustic.get('overall')
        if acoustic.get('overall')!='PASS': failures.append('RTX/model acoustic QA not PASS')

    binp=locate_vst3_binary(root)
    if not binp: failures.append('release VST3 binary missing')
    else:
        current=sha256(binp).lower();evidence['vst3_sha256']=current
        if val and str(val.get('vst3_sha256','')).lower()!=current: failures.append('validator evidence belongs to a different VST3 hash')
        for label,obj in [('Cubase',cubase),('Studio One',studio)]:
            if obj and str(obj.get('plugin_sha256','')).lower()!=current: failures.append(f'{label} evidence belongs to a different VST3 hash')
        if build:
            bh=str(((build.get('artifact') or {}).get('sha256') or '')).lower()
            if bh!=current: failures.append('build provenance belongs to a different VST3 hash')
        if acoustic:
            ah=str(acoustic.get('plugin_sha256','')).lower()
            if not ah: failures.append('acoustic evidence is not bound to a VST3 hash')
            elif ah!=current: failures.append('acoustic evidence belongs to a different VST3 hash')
    model_manifest_sha=verify_model_pack(root,failures,evidence)
    if acoustic:
        acoustic_model_sha=str(acoustic.get('model_manifest_sha256','')).lower()
        if not acoustic_model_sha: failures.append('acoustic evidence is not bound to a model manifest hash')
        elif model_manifest_sha and acoustic_model_sha!=model_manifest_sha:
            failures.append('acoustic evidence belongs to a different model manifest hash')

    if public:
        sig=load_json(ev/'authenticode-pass.json',failures,'Authenticode evidence')
        if sig:
            evidence['authenticode']=sig.get('status')
            if sig.get('release')!=RELEASE: failures.append(f'Authenticode evidence belongs to release {sig.get("release")!r}, expected {RELEASE}')
            if sig.get('status')!='Valid': failures.append('public release requires valid Authenticode evidence')
            if binp and str(sig.get('plugin_sha256','')).lower()!=evidence.get('vst3_sha256',''): failures.append('Authenticode evidence belongs to a different VST3 hash')

    status=('PUBLIC_RELEASE_APPROVED' if public else 'RC_APPROVED') if not failures else 'BLOCKED'
    result={
        'schema':1,'product':'SONICRAFT AI Strings Q4','release':RELEASE,'status':status,
        'checked_at':datetime.now(timezone.utc).isoformat(),'public_release':public,
        'evidence':evidence,'failures':failures,
    }
    out=ev/('public-release-gate.json' if public else 'rc-final-gate.json')
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    marker=ev/('PUBLIC_RELEASE_APPROVED.txt' if public else 'RC_APPROVED.txt')
    if failures:
        if marker.exists(): marker.unlink()
        return 2,result
    marker.write_text(f'{status}\n{result["checked_at"]}\n',encoding='ascii')
    return 0,result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));ap.add_argument('--public',action='store_true');a=ap.parse_args()
    code,result=evaluate(Path(a.root).resolve(),a.public)
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return code
if __name__=='__main__': raise SystemExit(main())
