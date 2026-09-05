from __future__ import annotations
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def evid(d):
    b=dict(d);b.pop('evidence_id',None)
    return hashlib.sha256(json.dumps(b,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def fake_pe64(path:Path):
    b=bytearray(512);b[:2]=b'MZ';b[0x3c:0x40]=(0x80).to_bytes(4,'little');b[0x80:0x84]=b'PE\0\0';b[0x84:0x86]=(0x8664).to_bytes(2,'little');b[0x98:0x9a]=(0x20b).to_bytes(2,'little');path.write_bytes(b)

def run(*args,**kw):return subprocess.run(list(map(str,args)),check=True,**kw)
with tempfile.TemporaryDirectory() as td0:
    td=Path(td0);build=td/'build'
    run('cmake','-S',ROOT,'-B',build,'-DSONICRAFT_BUILD_VST3=OFF','-DSONICRAFT_BUILD_PRODUCT_SHELL=OFF','-DSONICRAFT_BUILD_INPROCESS_ENGINE=ON',stdout=subprocess.DEVNULL)
    run('cmake','--build',build,'--parallel','2',stdout=subprocess.DEVNULL)
    e=build/('SonicraftInProcessEngineSmoke.exe' if os.name=='nt' else 'SonicraftInProcessEngineSmoke');g=build/('SonicraftInProcessPromotionGuardSmoke.exe' if os.name=='nt' else 'SonicraftInProcessPromotionGuardSmoke')
    cp=run(e,capture_output=True,text=True);assert 'voices=6' in cp.stdout and 'channels=24' in cp.stdout
    cp=run(g,td/'guard',capture_output=True,text=True);assert 'tamper=renderer_binding_failed' in cp.stdout and 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad' in cp.stdout

    # Strict tensor parity contract mechanics: six required scenarios pass only when reference/native agree.
    pairs=[]
    for i,sc in enumerate(('manual','assist','polyphony','q4_phrase','retake','multiout')):
        rng=np.random.default_rng(100+i);raw=rng.normal(size=(1,12,33)).astype('float32');ctx=rng.normal(size=(1,14,12)).astype('float32');vel=rng.normal(size=(1,64,4)).astype('float32');dec=rng.normal(size=(320,)).astype('float32');stage=rng.normal(size=(320,24)).astype('float32')
        r=td/f'r{i}.npz';n=td/f'n{i}.npz';np.savez(r,raw_controls=raw,frontier_context=ctx,renderer_velocity=vel,decoder_audio=dec,stage_audio=stage);np.savez(n,raw_controls=raw.copy(),frontier_context=ctx.copy(),renderer_velocity=vel.copy(),decoder_audio=dec.copy(),stage_audio=stage.copy());pairs.append({'scenario':sc,'reference':r.name,'native':n.name})
    man=td/'pairs.json';man.write_text(json.dumps({'pairs':pairs}));par=td/'parity.json';run(sys.executable,ROOT/'training/scripts/benchmark_inprocess_parity_v26.py','--manifest',man,'--out',par,stdout=subprocess.DEVNULL);pd=json.loads(par.read_text());assert pd['passed'] and pd['pair_count']==6
    # Changing authored pitch in native fixtures must fail even if everything else matches.
    z=np.load(td/'n0.npz');bad={k:z[k] for k in z.files};bad['raw_controls']=bad['raw_controls'].copy();bad['raw_controls'][0,0,0]+=1;np.savez(td/'n0.npz',**bad);badcp=subprocess.run([sys.executable,str(ROOT/'training/scripts/benchmark_inprocess_parity_v26.py'),'--manifest',str(man),'--out',str(td/'badparity.json')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);assert badcp.returncode!=0 and 'midi_authority_parity' in json.loads((td/'badparity.json').read_text())['reasons'][0]
    # Restore good parity for promotion mechanics.
    np.savez(td/'n0.npz',**{k:np.load(td/'r0.npz')[k] for k in np.load(td/'r0.npz').files});run(sys.executable,ROOT/'training/scripts/benchmark_inprocess_parity_v26.py','--manifest',man,'--out',par,stdout=subprocess.DEVNULL)

    # Pure-native Windows bundle is Python/service-free and cryptographically bound.
    bun=td/'bundle';bun.mkdir();fake_pe64(bun/'onnxruntime.dll');fake_pe64(bun/'SonicraftAIStringsProductShell.exe');(bun/'renderer_frontier.ort').write_bytes(b'renderer');(bun/'strings_vae64_decoder.ort').write_bytes(b'decoder')
    be=td/'bundle.json';run(sys.executable,ROOT/'training/scripts/verify_inprocess_bundle_v26.py','--bundle',bun,'--platform','Windows','--out',be,stdout=subprocess.DEVNULL);bd=json.loads(be.read_text());assert bd['passed'] and bd['python_free'] and bd['service_free']
    abx={'schema':2,'transparency_pass':True,'listener_count':5,'trial_count':80,'accuracy':.51};(td/'abx.json').write_text(json.dumps(abx))
    nat={'schema':2,'promotion_pass':True,'runtime_promotion_id':'b'*64};(td/'native.json').write_text(json.dumps(nat))
    lat={'schema':1,'promotion_pass':True,'ultra_low_latency_promotion_id':'c'*64};(td/'lat.json').write_text(json.dumps(lat))
    promo=td/'promo.json';lock=td/'inprocess_promotion_v26.lock';run(sys.executable,ROOT/'training/scripts/build_inprocess_promotion_v26.py','--bundle-evidence',be,'--parity',par,'--runtime-abx',td/'abx.json','--native-promotion',td/'native.json','--ultra-low-latency-promotion',td/'lat.json','--out',promo,'--lock',lock,stdout=subprocess.DEVNULL);pr=json.loads(promo.read_text());assert pr['promotion_pass'] and len(pr['inprocess_promotion_id'])==64 and lock.read_text().startswith('SONICRAFT_INPROCESS_PROMOTION_V26')
    # Artifact replacement after audit invalidates formal promotion.
    (bun/'renderer_frontier.ort').write_bytes(b'changed');bad=subprocess.run([sys.executable,str(ROOT/'training/scripts/build_inprocess_promotion_v26.py'),'--bundle-evidence',str(be),'--parity',str(par),'--runtime-abx',str(td/'abx.json'),'--native-promotion',str(td/'native.json'),'--ultra-low-latency-promotion',str(td/'lat.json'),'--out',str(td/'badpromo.json'),'--lock',str(td/'bad.lock')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);assert bad.returncode!=0

    # Source contracts: product shell uses a hybrid in-process-first renderer; production lock is mandatory except explicit unsafe dev mode.
    hy=(ROOT/'standalone/hybrid_renderer_v26.cpp').read_text();ort=(ROOT/'standalone/ort_native_session_v26.cpp').read_text();win=(ROOT/'standalone/win32/sonicraft_product_shell_win32_v26.cpp').read_text();cm=(ROOT/'CMakeLists.txt').read_text()
    for t in ('SONICRAFT_INPROCESS_PROMOTION_LOCK','verifyPromotionLock','SONICRAFT_INPROCESS_UNSAFE_DEV'):assert t in hy
    for t in ('Ort::Session','renderer_.Run','decoder_.Run','articulation_curve','frontier_context'):assert t in ort
    assert 'HybridRendererV26 renderer' in win and 'g->renderer.render' in win and 'Renderer: READY' in win
    assert 'SONICRAFT_ORT_SDK_ROOT' in cm and 'sonicraft_product_shell_win32_v26.cpp' in cm
print('v2.6 In-Process Neural Engine smoke PASS',{'cpp_e2e':'events→polyphony→33d/Q4/phrase→few-step→decoder→24ch','production_guard':'promotion lock + SHA-256','formal_parity_scenarios':6,'python_service_in_formal_bundle':False,'consumer_neural_params_added':0})
