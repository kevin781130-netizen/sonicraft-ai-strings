"""v2.4 fail-closed runtime backend selector.

AUTO chooses ORT only when a native-runtime promotion file is present, its bound footprint
report is intact, and every promoted artifact still matches SHA-256. Otherwise AUTO keeps the
proven Torch path. Explicit SONICRAFT_RUNTIME=torch/ort remains an expert override.
"""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path

def _load(p:Path):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return None

def _evidence_ok(d):
    if not isinstance(d,dict) or not d.get('evidence_id'):return False
    x=dict(d);eid=x.pop('evidence_id',None)
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()==eid

def _artifact_binding_ok(foot):
    try:
        root=Path(str(foot.get('bundle','')))
        arts=foot.get('artifacts') or []
        if not root.is_dir() or not arts:return False
        for e in arts:
            p=root/str(e.get('path',''))
            if not p.is_file() or p.stat().st_size!=int(e.get('bytes',-1)):return False
            if hashlib.sha256(p.read_bytes()).hexdigest()!=str(e.get('sha256','')):return False
        return True
    except Exception:return False

def promoted_ort_ready(app_home:Path,model_dir:Path):
    promo_path=Path(os.getenv('SONICRAFT_NATIVE_PROMOTION','').strip() or (app_home/'Runtime'/'native_runtime_promotion.json'))
    foot_path=Path(os.getenv('SONICRAFT_NATIVE_FOOTPRINT','').strip() or (app_home/'Runtime'/'native_runtime_footprint.json'))
    promo,foot=_load(promo_path),_load(foot_path)
    if not promo or not foot:return False,'promotion evidence missing'
    if int(promo.get('schema',0))<2 or not promo.get('promotion_pass') or len(str(promo.get('runtime_promotion_id','')))!=64:return False,'promotion invalid'
    if int(foot.get('schema',0))<3 or not foot.get('passed') or not _evidence_ok(foot) or not _artifact_binding_ok(foot):return False,'footprint/artifact binding invalid'
    if promo.get('footprint_evidence_id')!=foot.get('evidence_id'):return False,'promotion/footprint mismatch'
    ort_dir=Path(os.getenv('SONICRAFT_ORT_DIR','').strip() or (model_dir/'ORT'))
    manifest=ort_dir/'export_manifest.json'
    if not manifest.is_file():return False,'ORT export manifest missing'
    return True,f'promoted ORT {promo.get("runtime_promotion_id","")[:12]}'

def select_backend(app_home:Path,model_dir:Path,requested='auto'):
    requested=str(requested or os.getenv('SONICRAFT_RUNTIME','auto')).strip().lower()
    if requested in ('torch','ort'):return requested,'explicit override'
    ok,detail=promoted_ort_ready(Path(app_home),Path(model_dir))
    return ('ort',detail) if ok else ('torch','AUTO fallback: '+detail)
