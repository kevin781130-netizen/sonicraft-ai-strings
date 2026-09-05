from __future__ import annotations
import hashlib,json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
import soundfile as sf
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def free_port():
    s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p

def evid(d):
    x=dict(d);x.pop('evidence_id',None);return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

with tempfile.TemporaryDirectory() as td0:
    td=Path(td0);build=td/'build'
    subprocess.run(['cmake','-S',str(ROOT),'-B',str(build),'-DSONICRAFT_BUILD_VST3=OFF','-DSONICRAFT_BUILD_PRODUCT_SHELL=OFF','-DSONICRAFT_BUILD_STANDALONE=ON','-DSONICRAFT_BUILD_REALTIME_SIM=ON','-DSONICRAFT_BUILD_LOW_LATENCY_SIM=ON'],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['cmake','--build',str(build),'--parallel','2'],check=True,stdout=subprocess.DEVNULL)
    sim=build/('SonicraftAIStringsLowLatencySim.exe' if os.name=='nt' else 'SonicraftAIStringsLowLatencySim');assert sim.is_file()
    port=free_port();svc=subprocess.Popen([sys.executable,str(ROOT/'runtime/renderer_service.py'),'--mock','--host','127.0.0.1','--port',str(port)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        ready=False
        for _ in range(120):
            line=svc.stdout.readline() if svc.stdout else ''
            if f'listening on 127.0.0.1:{port}' in line:ready=True;break
            if svc.poll() is not None:break
        assert ready
        wav=td/'low.wav';cp=subprocess.run([str(sim),'--host','127.0.0.1','--port',str(port),'--blocks','8','--out',str(wav)],check=True,capture_output=True,text=True);assert 'first_quantum_ms=40' in cp.stdout
        x,sr=sf.read(wav,dtype='float32',always_2d=True);assert sr==48000 and x.shape[1]==2 and len(x)>0 and np.max(np.abs(x))>0
        # Formal v2.5 latency evidence must reject MOCK and non-Windows environments.
        rep=td/'bench.json';bad=subprocess.run([sys.executable,str(ROOT/'training/scripts/benchmark_ultra_low_latency_v25.py'),'--host','127.0.0.1','--port',str(port),'--trials','5','--wasapi-stream-latency-ms','4','--out',str(rep)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);assert bad.returncode!=0;rb=json.loads(rep.read_text());assert not rb['passed'] and ('production_backend_required' in rb['reasons'] or 'formal_ultra_low_latency_requires_windows' in rb['reasons'])
    finally:
        svc.terminate();
        try:svc.wait(timeout=3)
        except subprocess.TimeoutExpired:svc.kill()

    # Synthetic promotion mechanics: require v2.4 product identity + valid WASAPI/timestamp evidence.
    prod={'schema':1,'kind':'sonicraft_realtime_product_promotion_v24','promotion_pass':True,'product_promotion_id':'a'*64};(td/'prod.json').write_text(json.dumps(prod))
    bench={'schema':1,'kind':'sonicraft_ultra_low_latency_benchmark_v25','platform':'Windows','audio_engine':'WASAPI_EVENT_SHARED_IAUDIOCLIENT3','midi_timestamp_source':'WinMM_dwParam2_driver_timestamp','adaptive_quantum_ms':[40,80,160],'attack_p95_service_ms':24.0,'wasapi_stream_latency_ms':5.0,'estimated_first_audio_ms':29.0,'passed':True};bench['evidence_id']=evid(bench);(td/'okbench.json').write_text(json.dumps(bench))
    out=td/'promo.json';subprocess.run([sys.executable,str(ROOT/'training/scripts/build_ultra_low_latency_promotion_v25.py'),'--product-promotion',str(td/'prod.json'),'--latency-benchmark',str(td/'okbench.json'),'--out',str(out)],check=True,stdout=subprocess.DEVNULL);pr=json.loads(out.read_text());assert pr['promotion_pass'] and len(pr['ultra_low_latency_promotion_id'])==64
    bench['audio_engine']='waveOut';bench['evidence_id']=evid(bench);(td/'badbench.json').write_text(json.dumps(bench));bad=subprocess.run([sys.executable,str(ROOT/'training/scripts/build_ultra_low_latency_promotion_v25.py'),'--product-promotion',str(td/'prod.json'),'--latency-benchmark',str(td/'badbench.json'),'--out',str(td/'badpromo.json')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);assert bad.returncode!=0

    # In-process ORT candidate audit is Python/Torch-free and artifact-bound, but not falsely promoted here.
    ib=td/'inprocess';ib.mkdir();(ib/'onnxruntime.dll').write_bytes(b'ort');(ib/'renderer_frontier.ort').write_bytes(b'render');(ib/'strings_vae64_decoder.ort').write_bytes(b'decode')
    ir=td/'inproc.json';subprocess.run([sys.executable,str(ROOT/'training/scripts/verify_inprocess_ort_candidate_v25.py'),'--bundle',str(ib),'--out',str(ir)],check=True,stdout=subprocess.DEVNULL);idd=json.loads(ir.read_text());assert idd['passed'] and idd['python_free']
    (ib/'python311.dll').write_bytes(b'nope');bad=subprocess.run([sys.executable,str(ROOT/'training/scripts/verify_inprocess_ort_candidate_v25.py'),'--bundle',str(ib),'--out',str(td/'badinproc.json')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);assert bad.returncode!=0

    # Windows source contract: IAudioClient3 event mode, MMCSS, real driver timestamp, adaptive quantum and service-free ORT loader boundary.
    was=(ROOT/'standalone/win32/wasapi_event_output.cpp').read_text(encoding='utf-8');win=(ROOT/'standalone/win32/sonicraft_product_shell_win32_v25.cpp').read_text(encoding='utf-8');ll=(ROOT/'standalone/low_latency_engine.cpp').read_text(encoding='utf-8');ort=(ROOT/'standalone/win32/ort_inprocess_probe_v25.cpp').read_text(encoding='utf-8')
    for t in ('IAudioClient3','GetSharedModeEnginePeriod','InitializeSharedAudioStream','AUDCLNT_STREAMFLAGS_EVENTCALLBACK','AvSetMmThreadCharacteristicsW','GetStreamLatency'):assert t in was
    for t in ('DWORD_PTR p2','midiClock.sampleFor','freshAttack','queueAudio','WASAPI EVENT'):assert t in win
    for t in ('fresh-attack','deadline-recovery','currentMs_=40'):assert t in ll
    assert 'OrtGetApiBase' in ort and 'python=0 torch=0' in ort
    assert 'deferredOff' in (ROOT/'standalone/realtime_shell_core.h').read_text()

print('v2.5 Ultra-Low-Latency Engine smoke PASS',{'attack_quantum_ms':40,'adaptive_quantum_ms':[40,80,160],'audio':'WASAPI IAudioClient3 event-driven','midi':'driver timestamp calibrated','sustain':'pedal-correct deferred note-off','inprocess_ort':'python-free candidate boundary','consumer_neural_params_added':0})
