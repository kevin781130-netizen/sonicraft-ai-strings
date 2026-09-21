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

    # Synthetic fixtures are confined to this temporary tree, never real evidence.
    blind_base={'release':RELEASE,'product':'SONICRAFT AI Strings Q4','overall':'PASS',
                'plugin_sha256':ph,'model_manifest_sha256':mh,
                'protocol_sha256':'12'*32,'raw_results_sha256':'34'*32,
                'protocol':{'double_blind':True,'randomized':True,'negative_control':True,
                            'listener_count':5,'trial_count':60},
                'results':{key:{'status':'PASS'} for key in
                           ('sample_size','realism','technique_identity','negative_control')}}
    blind_path=ev/'blind-acoustic-qa.json'
    blind_path.write_text(json.dumps(blind_base))

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

    # Every malformed/missing evidence file must block and revoke BOTH markers.
    paths=[ev/name for name in ('build-provenance.json','validator-pass.json',
           'host-qa-cubase.json','host-qa-studio-one.json','acoustic-qa.json',
           'blind-acoustic-qa.json','authenticode-pass.json')]+[mp]
    for path in paths:
        original=path.read_bytes()
        for payload in (None, b'{}', b'[]', b'null', b'"PASS"', b'{broken'):
            for marker in ('RC_APPROVED.txt','PUBLIC_RELEASE_APPROVED.txt'):
                (ev/marker).write_text('stale approval')
            if payload is None: path.unlink()
            else: path.write_bytes(payload)
            code,res=evaluate(r,True)
            assert code==2 and res['status']=='BLOCKED', (path,payload,res)
            assert not (ev/'RC_APPROVED.txt').exists()
            assert not (ev/'PUBLIC_RELEASE_APPROVED.txt').exists()
            path.write_bytes(original)

    for field,value in [('protocol',[]),('results',['invalid']),
                        ('plugin_sha256','00'*32),('model_manifest_sha256','00'*32)]:
        bad=dict(blind_base);bad[field]=value
        blind_path.write_text(json.dumps(bad))
        code,res=evaluate(r,False);assert code==2,res
    for section in ('sample_size','realism','technique_identity','negative_control'):
        bad=json.loads(json.dumps(blind_base));bad['results'][section]['status']='FAIL'
        blind_path.write_text(json.dumps(bad))
        code,res=evaluate(r,False);assert code==2,res
    blind_path.write_text(json.dumps(blind_base))
    original=mp.read_bytes()
    bad=json.loads(original);bad['release_approved']='false'
    mp.write_text(json.dumps(bad))
    code,res=evaluate(r,False)
    assert code==2 and 'model manifest is not commercial_safe + release_approved' in res['failures']
    mp.write_bytes(original)
    code,res=evaluate(r,True);assert code==0,res
print('SONICRAFT v7.0 fail-closed/hash-bound final gate smoke PASS')
