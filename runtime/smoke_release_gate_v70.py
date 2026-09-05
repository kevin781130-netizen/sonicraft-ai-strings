from __future__ import annotations
import hashlib,json,tempfile
from pathlib import Path
from release_gate_v70 import evaluate

RELEASE='7.0.0-rc2'
SDK='9fad9770f2ae8542ab1a548a68c1ad1ac690abe0'
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory() as td:
    r=Path(td);ev=r/'release'/'rc_evidence';ev.mkdir(parents=True)
    code,res=evaluate(r,False)
    assert code==2 and res['status']=='BLOCKED' and not (ev/'RC_APPROVED.txt').exists()

    bdir=r/'release'/'SONICRAFT AI Strings Q4.vst3'/'Contents'/'x86_64-win';bdir.mkdir(parents=True)
    binp=bdir/'SONICRAFT AI Strings Q4.vst3';binp.write_bytes(b'MZ'+b'rc-test'*100);ph=h(binp)
    md=r/'release'/'prebuilt'/'Models';md.mkdir(parents=True)
    w=md/'weights.onnx';w.write_bytes(b'weights')
    mp=md/'release_model_manifest.json'
    mp.write_text(json.dumps({'commercial_safe':True,'release_approved':True,'files':[{'name':'weights.onnx','sha256':h(w)}]}))
    mh=h(mp)

    (ev/'build-provenance.json').write_text(json.dumps({'release':RELEASE,'status':'PASS','artifact':{'sha256':ph},'vst3_sdk':{'version':'3.8.0','commit':SDK}}))
    (ev/'validator-pass.json').write_text(json.dumps({'release':RELEASE,'passed':True,'vst3_sha256':ph,'vst3_sdk_version':'3.8.0','vst3_sdk_commit':SDK}))
    host_base={'release':RELEASE,'overall':'PASS','plugin_sha256':ph,'host_version':'99.0','host_exe':'C:/Program Files/TestHost/TestHost.exe','host_exe_sha256':'ab'*32}
    (ev/'host-qa-cubase.json').write_text(json.dumps(host_base))
    (ev/'host-qa-studio-one.json').write_text(json.dumps(host_base))
    (ev/'acoustic-qa.json').write_text(json.dumps({'release':RELEASE,'overall':'PASS','plugin_sha256':ph,'model_manifest_sha256':mh}))

    code,res=evaluate(r,False);assert code==0 and res['status']=='RC_APPROVED' and (ev/'RC_APPROVED.txt').exists(),res

    # Stale host evidence must revoke approval.
    stale=dict(host_base);stale['plugin_sha256']='00'*32
    (ev/'host-qa-cubase.json').write_text(json.dumps(stale))
    code,res=evaluate(r,False);assert code==2 and 'different VST3 hash' in ' '.join(res['failures']) and not (ev/'RC_APPROVED.txt').exists()

    # Restore host evidence, then mutate model pack: acoustic evidence must be revoked too.
    (ev/'host-qa-cubase.json').write_text(json.dumps(host_base))
    mp.write_text(json.dumps({'commercial_safe':True,'release_approved':True,'files':[{'name':'weights.onnx','sha256':h(w)}],'revision':2}))
    code,res=evaluate(r,False);assert code==2 and 'different model manifest hash' in ' '.join(res['failures'])
    mp.write_text(json.dumps({'commercial_safe':True,'release_approved':True,'files':[{'name':'weights.onnx','sha256':h(w)}]}))

    # Public release must still block without hash-bound signature evidence.
    code,res=evaluate(r,True);assert code==2 and res['status']=='BLOCKED'
    (ev/'authenticode-pass.json').write_text(json.dumps({'release':RELEASE,'status':'Valid','plugin_sha256':ph}))
    code,res=evaluate(r,True);assert code==0 and res['status']=='PUBLIC_RELEASE_APPROVED',res
print('SONICRAFT v7.0 fail-closed/hash-bound final gate smoke PASS')
