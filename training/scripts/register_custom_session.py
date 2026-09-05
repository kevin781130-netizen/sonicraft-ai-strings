from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

def digest(p: Path):
    h=hashlib.sha256();
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',required=True)
    ap.add_argument('--rights-release',required=True,help='Signed PDF or immutable rights-release document')
    ap.add_argument('--out',default='datasets/owned/custom_session_clearance.json')
    a=ap.parse_args(); m=Path(a.manifest); r=Path(a.rights_release)
    if not m.exists() or not r.exists(): sys.exit('Manifest or signed rights-release file missing.')
    # This does not decide legal sufficiency; it prevents accidental training without a recorded clearance artifact.
    obj={'dataset':'custom_owned_session','manifest':str(m),'manifest_sha256':digest(m),'rights_release':str(r),'rights_release_sha256':digest(r),
         'status':'RECORDED_FOR_MANUAL_LEGAL_APPROVAL','release_blocked':True}
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(obj,indent=2),encoding='utf-8')
    print('Registered custom session evidence:',out)
    print('NOTE: release_blocked remains TRUE until the agreement is manually/legal-reviewed and registry/provenance is explicitly approved.')
if __name__=='__main__': main()
