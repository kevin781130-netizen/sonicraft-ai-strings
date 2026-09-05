from __future__ import annotations
import hashlib,json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
import numpy as np
import soundfile as sf
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from runtime_backend_selector_v24 import select_backend

def free_port():
    s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p

def evid(d):
    x=dict(d);x.pop('evidence_id',None);return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def fake_pe(path:Path):
    b=bytearray(512);b[:2]=b'MZ';off=0x80;b[0x3c:0x40]=off.to_bytes(4,'little');b[off:off+4]=b'PE\0\0';b[off+4:off+6]=b'\x64\x86';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)

with tempfile.TemporaryDirectory() as td0:
    td=Path(td0)
    # 1) Cross-platform rolling-window core compiles without VST3 and renders 24ch -> standalone stereo.
    build=td/'build'
    subprocess.run(['cmake','-S',str(ROOT),'-B',str(build),'-DSONICRAFT_BUILD_VST3=OFF','-DSONICRAFT_BUILD_STANDALONE=ON','-DSONICRAFT_BUILD_REALTIME_SIM=ON'],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['cmake','--build',str(build),'--parallel','2'],check=True,stdout=subprocess.DEVNULL)
    sim=build/('SonicraftAIStringsRealtimeSim.exe' if os.name=='nt' else 'SonicraftAIStringsRealtimeSim');assert sim.is_file()
    port=free_port();svc=subprocess.Popen([sys.executable,str(ROOT/'runtime/renderer_service.py'),'--mock','--host','127.0.0.1','--port',str(port)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        ready=False
        for _ in range(120):
            line=svc.stdout.readline() if svc.stdout else ''
            if f'listening on 127.0.0.1:{port}' in line:ready=True;break
            if svc.poll() is not None:break
        assert ready
        wav=td/'rt.wav';subprocess.run([str(sim),'--host','127.0.0.1','--port',str(port),'--quantum-ms','160','--blocks','6','--out',str(wav)],check=True,stdout=subprocess.DEVNULL)
        x,sr=sf.read(wav,dtype='float32',always_2d=True);assert sr==48000 and x.shape==(46080,2) and np.max(np.abs(x))>0
        # Mock must NEVER satisfy formal realtime promotion timing evidence.
        rep=td/'mock_bench.json';bad=subprocess.run([sys.executable,str(ROOT/'training/scripts/benchmark_realtime_preview_v24.py'),'--host','127.0.0.1','--port',str(port),'--trials','6','--max-p95-ms','1000','--out',str(rep)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);assert bad.returncode!=0;rb=json.loads(rep.read_text());assert rb['backend']=='MOCK' and not rb['passed']
    finally:
        svc.terminate();
        try:svc.wait(timeout=3)
        except subprocess.TimeoutExpired:svc.kill()

    # 2) AUTO backend selection is promotion-bound and fail-closed on post-audit artifact tampering.
    app=td/'app';runtime=app/'Runtime';model=app/'Models';ort=model/'ORT';bundle=td/'nativebundle';runtime.mkdir(parents=True);ort.mkdir(parents=True);bundle.mkdir()
    (ort/'export_manifest.json').write_text('{}');art=bundle/'onnxruntime.dll';art.write_bytes(b'ort-runtime')
    foot={'schema':3,'kind':'sonicraft_native_runtime_footprint_v23','deployment_kind':'pure-native-ort','bundle':str(bundle),'files':1,'bytes':art.stat().st_size,'mib':art.stat().st_size/1024**2,'max_mib':160.0,'models':['renderer.ort','decoder.ort'],'onnxruntime_binaries':['onnxruntime.dll'],'banned_framework_hits':[],'reasons':[],'passed':True,'artifacts':[{'path':'onnxruntime.dll','bytes':art.stat().st_size,'sha256':hashlib.sha256(art.read_bytes()).hexdigest()}]};foot['evidence_id']=evid(foot);(runtime/'native_runtime_footprint.json').write_text(json.dumps(foot))
    promo={'schema':2,'kind':'sonicraft_native_runtime_promotion_v23','deployment_kind':'pure-native-ort','runtime':'onnxruntime-reduced','acoustic_promotion_id':'a'*64,'footprint_evidence_id':foot['evidence_id'],'numerical_evidence_id':'b'*64,'benchmark_evidence_id':'c'*64,'runtime_abx_accuracy':.5,'p95_rtf':.3,'reasons':[],'promotion_pass':True};promo['runtime_promotion_id']=hashlib.sha256(json.dumps(promo,sort_keys=True,separators=(',',':')).encode()).hexdigest();(runtime/'native_runtime_promotion.json').write_text(json.dumps(promo))
    assert select_backend(app,model,'auto')[0]=='ort';art.write_bytes(b'tampered');assert select_backend(app,model,'auto')[0]=='torch';assert select_backend(app,model,'ort')[0]=='ort'

    # 3) Product-shell promotion mechanics require native promotion, non-mock realtime evidence and a bound PE64 shell bundle.
    native={'schema':2,'promotion_pass':True,'runtime_promotion_id':'d'*64};(td/'native.json').write_text(json.dumps(native))
    bench={'schema':1,'kind':'sonicraft_realtime_preview_benchmark_v24','sample_rate':48000,'quantum_ms':160.0,'trials':80,'median_first_audio_ms':58.0,'p95_first_audio_ms':91.0,'max_p95_ms':120.0,'deadline_miss_rate':0.0,'cache_hits':0,'backend':'ORT','passed':True};bench['evidence_id']=evid(bench);(td/'bench.json').write_text(json.dumps(bench))
    shell=td/'shell';fake_pe(shell/'SonicraftAIStringsProductShell.exe');fake_pe(shell/'SONICRAFT_AI_Renderer_Service.exe')
    shellrep=td/'shellrep.json';subprocess.run([sys.executable,str(ROOT/'training/scripts/verify_product_shell_bundle_v24.py'),'--bundle',str(shell),'--out',str(shellrep)],check=True,stdout=subprocess.DEVNULL)
    out=td/'product.json';subprocess.run([sys.executable,str(ROOT/'training/scripts/build_product_shell_promotion_v24.py'),'--native-promotion',str(td/'native.json'),'--realtime-benchmark',str(td/'bench.json'),'--shell-bundle',str(shellrep),'--out',str(out)],check=True,stdout=subprocess.DEVNULL);pr=json.loads(out.read_text());assert pr['promotion_pass'] and len(pr['product_promotion_id'])==64
    (shell/'SonicraftAIStringsProductShell.exe').write_bytes(b'tamper');bad=subprocess.run([sys.executable,str(ROOT/'training/scripts/build_product_shell_promotion_v24.py'),'--native-promotion',str(td/'native.json'),'--realtime-benchmark',str(td/'bench.json'),'--shell-bundle',str(shellrep),'--out',str(td/'bad.json')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);assert bad.returncode!=0

    # 4) Windows source contract: no external GUI/audio framework, strict-authority defaults and native MIDI/audio APIs are present.
    win=(ROOT/'standalone/win32/sonicraft_product_shell_win32.cpp').read_text(encoding='utf-8')
    for token in ('midiInOpen','waveOutOpen','Smart Dynamics','Smart Articulation','Independent Polyphony','IDC_FEED0','rolling 160 ms') : assert token in win
    for banned in ('JUCE','QtWidgets','SDL_','ImGui::'): assert banned not in win
    assert 'bool smartDynamics=false' in (ROOT/'standalone/realtime_shell_core.h').read_text()

print('v2.4 Realtime Product Shell smoke PASS',{'rolling_window_ms':160,'mixer_feeds':11,'native_ui':'Win32+WinMM','auto_runtime':'promotion-bound ORT else Torch','mock_promotion':'blocked','consumer_neural_params_added':0})
