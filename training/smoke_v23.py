from __future__ import annotations
import hashlib,json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
import numpy as np
import soundfile as sf
ROOT=Path(__file__).resolve().parents[1]

def free_port():
    s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p

with tempfile.TemporaryDirectory() as td0:
    td=Path(td0)
    # 1) Standalone builds without VST3 SDK and renders both stereo and 24ch through the real wire protocol.
    build=td/'build'
    subprocess.run(['cmake','-S',str(ROOT),'-B',str(build),'-DSONICRAFT_BUILD_VST3=OFF','-DSONICRAFT_BUILD_STANDALONE=ON'],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['cmake','--build',str(build),'--parallel','2'],check=True,stdout=subprocess.DEVNULL)
    exe=build/('SonicraftAIStringsStandalone.exe' if os.name=='nt' else 'SonicraftAIStringsStandalone')
    assert exe.is_file()
    port=free_port();svc=subprocess.Popen([sys.executable,str(ROOT/'runtime/renderer_service.py'),'--mock','--host','127.0.0.1','--port',str(port)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        ready=False
        for _ in range(100):
            line=svc.stdout.readline() if svc.stdout else ''
            if f'listening on 127.0.0.1:{port}' in line:ready=True;break
            if svc.poll() is not None:break
        assert ready
        stereo=td/'stereo.wav';multi=td/'multi.wav'
        subprocess.run([str(exe),'--host','127.0.0.1','--port',str(port),'--seconds','.25','--out',str(stereo)],check=True,stdout=subprocess.DEVNULL)
        subprocess.run([str(exe),'--host','127.0.0.1','--port',str(port),'--seconds','.20','--multiout','--out',str(multi)],check=True,stdout=subprocess.DEVNULL)
        a,sr=sf.read(stereo,dtype='float32',always_2d=True);b,sr2=sf.read(multi,dtype='float32',always_2d=True)
        assert sr==sr2==48000 and a.shape[1]==2 and b.shape[1]==24 and np.max(np.abs(a))>0 and np.max(np.abs(b))>0
    finally:
        svc.terminate();
        try:svc.wait(timeout=3)
        except subprocess.TimeoutExpired:svc.kill()

    # 2) Clean-room room capture: known synthetic IR -> sweep recording -> recovered 11-feed profile.
    sweep=td/'sweep.wav';subprocess.run([sys.executable,str(ROOT/'training/scripts/generate_room_sweep_v23.py'),'--out',str(sweep),'--seconds','1.2','--tail-seconds','.2'],check=True,stdout=subprocess.DEVNULL)
    x,sr=sf.read(sweep,dtype='float32');rec=td/'rec';rec.mkdir();names=('spot_l','spot_c','spot_r','tree_l','tree_c','tree_r','wide_l','wide_r','room_l','room_r','rear')
    for i,n in enumerate(names):
        h=np.zeros((192,2),np.float32);h[18+i,0]=.8;h[22+i,1]=.6;y=np.stack([np.convolve(x,h[:,0]),np.convolve(x,h[:,1])],1).astype(np.float32);sf.write(rec/f'{n}.wav',y,sr,subtype='FLOAT')
    profile=td/'room.json';irs=td/'irs';subprocess.run([sys.executable,str(ROOT/'training/scripts/recover_room_irs_v23.py'),'--sweep',str(sweep),'--recordings-dir',str(rec),'--ir-out-dir',str(irs),'--profile-out',str(profile),'--rights-confirmed','--session-note','v2.3 synthetic clean-room smoke'],check=True,stdout=subprocess.DEVNULL)
    rp=json.loads(profile.read_text());cap=json.loads(profile.with_suffix('.capture.json').read_text());assert len(rp['feeds'])==11 and cap['rights_confirmed'] and len(cap['evidence_id'])==64

    # 3) v2.3 footprint/promotion contract with latency evidence and post-audit artifact binding.
    bundle=td/'bundle';(bundle/'Lib/site-packages/numpy').mkdir(parents=True);(bundle/'Lib/site-packages/onnxruntime').mkdir(parents=True);(bundle/'Runtime').mkdir();(bundle/'Models').mkdir()
    for p,data in [(bundle/'python312.dll',b'py'),(bundle/'python.exe',b'pyexe'),(bundle/'onnxruntime.dll',b'ort'),(bundle/'Lib/site-packages/numpy/__init__.py',b'numpy'),(bundle/'Lib/site-packages/onnxruntime/state.pyd',b'ortpyd'),(bundle/'Runtime/renderer_service.py',b'# service'),(bundle/'Models/renderer.ort',b'renderer'),(bundle/'Models/decoder.ort',b'decoder')]:p.write_bytes(data)
    fp=td/'footprint.json';subprocess.run([sys.executable,str(ROOT/'training/scripts/verify_native_runtime_bundle_v23.py'),'--bundle',str(bundle),'--out',str(fp)],check=True,stdout=subprocess.DEVNULL);f=json.loads(fp.read_text());assert f['schema']==3 and f['passed']
    num={'schema':1,'passed':True,'pair_count':3};num['evidence_id']=hashlib.sha256(json.dumps(num,sort_keys=True,separators=(',',':')).encode()).hexdigest();(td/'num.json').write_text(json.dumps(num))
    bench={'schema':1,'kind':'sonicraft_runtime_benchmark_v23','p95_rtf':.4,'max_p95_rtf':1.,'passed':True};bench['evidence_id']=hashlib.sha256(json.dumps(bench,sort_keys=True,separators=(',',':')).encode()).hexdigest();(td/'bench.json').write_text(json.dumps(bench))
    (td/'abx.json').write_text(json.dumps({'schema':2,'transparency_pass':True,'listener_count':5,'trial_count':100,'accuracy':.49}))
    (td/'ac.json').write_text(json.dumps({'promotion_pass':True,'promotion_id':'a'*64}))
    promo=td/'promo.json';subprocess.run([sys.executable,str(ROOT/'training/scripts/build_native_runtime_promotion_v23.py'),'--footprint',str(fp),'--numerical',str(td/'num.json'),'--runtime-abx',str(td/'abx.json'),'--benchmark',str(td/'bench.json'),'--acoustic-promotion',str(td/'ac.json'),'--out',str(promo)],check=True,stdout=subprocess.DEVNULL);pr=json.loads(promo.read_text());assert pr['promotion_pass'] and len(pr['runtime_promotion_id'])==64
    (bundle/'Models/renderer.ort').write_bytes(b'tampered')
    bad=subprocess.run([sys.executable,str(ROOT/'training/scripts/build_native_runtime_promotion_v23.py'),'--footprint',str(fp),'--numerical',str(td/'num.json'),'--runtime-abx',str(td/'abx.json'),'--benchmark',str(td/'bench.json'),'--acoustic-promotion',str(td/'ac.json'),'--out',str(td/'bad.json')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    assert bad.returncode!=0

print('v2.3 Native Production Pass smoke PASS',{'standalone':'2ch+24ch','room_capture_feeds':11,'native_runtime':'size+hash+latency+ABX+acoustic promotion','consumer_neural_params_added':0})
