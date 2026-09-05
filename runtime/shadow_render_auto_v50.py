"""SONICRAFT v5.0 Local Shadow Render client + compiled-MIDI adapter.

Reuses renderer_service.py over its existing TCP protocol. It does not call model backends directly.
Long files are rendered in <=40 s chunks with 0.75 s overlap/crossfade. Every chunk receives the
full compiled event history, so notes/controls active before the chunk can be reconstructed by the
existing control builders.
"""
from __future__ import annotations
from pathlib import Path
import argparse, math, os, socket, subprocess, sys, time, wave
import numpy as np

from protocol import *
from compile_midi_performance_v29 import parse_midi
from compile_musicxml_strings_v41 import KS_BASE,VOICE_CHANNELS

PHYS={27:112,28:113,29:114,30:115,31:116,33:117,34:118,35:119}
ENSEMBLE={36:120,37:121}
GESTURE={38:122}
MAX_EVENTS=32768
DEFAULT_CHUNK_SECONDS=40.0
DEFAULT_OVERLAP_SECONDS=.75

PART_FOR_CHANNEL={ch:p for p,chs in VOICE_CHANNELS.items() for ch in chs}

def _tempo_points(tracks):
    pts=[(0,500000)]
    for tr in tracks:
        for e in tr:
            if e.status==0xFF and e.data and e.data[0]==0x51 and len(e.data)>=4:
                pts.append((int(e.tick),(e.data[1]<<16)|(e.data[2]<<8)|e.data[3]))
    d={}
    for tick,us in pts:d[tick]=max(1,int(us))
    return sorted(d.items())

def _tick_to_seconds_fn(division,tempo):
    seg=[];sec=0.;last=0;us=tempo[0][1]
    for tick,new_us in tempo[1:]:
        tick=max(last,int(tick));seg.append((last,tick,sec,us));sec+=(tick-last)/float(division)*us/1e6;last=tick;us=new_us
    seg.append((last,10**18,sec,us))
    def f(tick):
        tick=int(tick)
        for a,b,s,u in seg:
            if a<=tick<b:return s+(tick-a)/float(division)*u/1e6
        a,b,s,u=seg[-1];return s+(tick-a)/float(division)*u/1e6
    return f

def _tempo_at_tick(tempo,tick):
    us=tempo[0][1]
    for t,u in tempo:
        if t>tick:break
        us=u
    return 60_000_000.0/max(1,us)

def _wire_part(part,lane):return (int(part)&3)|((int(lane)+1)<<2)
def _packed(base,stack):return (int(base)&0x0F)|((int(stack)&0x0F)<<4)

def compiled_midi_to_shadow_events_v50(path,sample_rate=48000,tail_seconds=1.5):
    fmt,division,tracks=parse_midi(Path(path));tempo=_tempo_points(tracks);to_sec=_tick_to_seconds_fn(division,tempo)
    controls={ch:[.62,.50,.90,.86,.50,1.,1.,.18,.50,0.,.50,.50,.38,0.] for ch in range(16)}
    base_art={ch:0 for ch in range(16)};stack={ch:0 for ch in range(16)}
    events=[];max_ps=0
    merged=sorted((e for tr in tracks for e in tr),key=lambda e:(e.tick,e.track,e.order))
    for e in merged:
        if e.status>=0xF0:continue
        hi=e.status&0xF0;ch=e.status&0x0F
        part=PART_FOR_CHANNEL.get(ch,max(0,min(3,e.track-1)))
        ps=int(round(to_sec(e.tick)*sample_rate));max_ps=max(max_ps,ps);bpm=float(_tempo_at_tick(tempo,e.tick))
        if hi==0xB0 and len(e.data)>=2:
            cc=int(e.data[0]);raw=int(e.data[1]);v=raw/127.0
            if cc==21:stack[ch]=max(0,min(15,int(round(v*15))))
            elif cc==22:controls[ch][0]=v
            elif cc==23:controls[ch][1]=v
            elif cc==24:controls[ch][10]=v
            elif cc==25:controls[ch][12]=v
            elif cc==26:controls[ch][11]=v
            elif cc==39:controls[ch][8]=v
            packed=_packed(base_art[ch],stack[ch]);wire=_wire_part(part,ch)
            if cc in PHYS:
                events.append({'project_sample':ps,'type':EVENT_CONTROL,'part':part,'voice_lane':ch,'wire_part':wire,'note':PHYS[cc],'articulation':packed,'velocity':v,'tempo_bpm':bpm,'controls':list(controls[ch])})
            elif cc in ENSEMBLE:
                events.append({'project_sample':ps,'type':EVENT_CONTROL,'part':part,'voice_lane':ch,'wire_part':wire,'note':ENSEMBLE[cc],'articulation':packed,'velocity':v,'tempo_bpm':bpm,'controls':list(controls[ch])})
            elif cc in GESTURE:
                events.append({'project_sample':ps,'type':EVENT_CONTROL,'part':part,'voice_lane':ch,'wire_part':wire,'note':GESTURE[cc],'articulation':packed,'velocity':v,'tempo_bpm':bpm,'controls':list(controls[ch])})
            elif cc in (21,22,23,24,25,26,39):
                events.append({'project_sample':ps,'type':EVENT_CONTROL,'part':part,'voice_lane':ch,'wire_part':wire,'note':0,'articulation':packed,'velocity':v,'tempo_bpm':bpm,'controls':list(controls[ch])})
            # Host-command CCs 102..119 on the conductor lane are intentionally not converted to
            # note-level control events. Shadow policy flags are fixed by render_policy_flags_v50().
            continue
        if hi==0x90 and len(e.data)>=2 and e.data[1]>0:
            note=int(e.data[0]);vel=e.data[1]/127.0;wire=_wire_part(part,ch)
            if KS_BASE<=note<KS_BASE+12:
                base_art[ch]=note-KS_BASE;controls[ch][9]=base_art[ch]/11.0
                packed=_packed(base_art[ch],stack[ch])
                events.append({'project_sample':ps,'type':EVENT_KEYSWITCH,'part':part,'voice_lane':ch,'wire_part':wire,'note':note,'articulation':packed,'velocity':0.0,'tempo_bpm':bpm,'controls':list(controls[ch])})
            else:
                packed=_packed(base_art[ch],stack[ch])
                events.append({'project_sample':ps,'type':EVENT_NOTE_ON,'part':part,'voice_lane':ch,'wire_part':wire,'note':note,'articulation':packed,'velocity':vel,'tempo_bpm':bpm,'controls':list(controls[ch])})
        elif (hi==0x80 or (hi==0x90 and len(e.data)>=2 and e.data[1]==0)) and len(e.data)>=1:
            note=int(e.data[0]);wire=_wire_part(part,ch)
            if KS_BASE<=note<KS_BASE+12:continue
            packed=_packed(base_art[ch],stack[ch])
            events.append({'project_sample':ps,'type':EVENT_NOTE_OFF,'part':part,'voice_lane':ch,'wire_part':wire,'note':note,'articulation':packed,'velocity':0.0,'tempo_bpm':bpm,'controls':list(controls[ch])})
    events.sort(key=lambda x:(int(x['project_sample']),0 if int(x['type'])==EVENT_CONTROL else 1))
    if len(events)>MAX_EVENTS:raise ValueError(f'compiled MIDI creates {len(events)} Shadow events; limit is {MAX_EVENTS}')
    end_sample=max(int(sample_rate*.25),max_ps+int(float(tail_seconds)*sample_rate))
    start_bpm=float(_tempo_at_tick(tempo,0))
    return events,end_sample,start_bpm

def render_policy_flags_v50(multi_out=False):
    # Mirrors Processor defaults: Assist, neutral style, written MIDI authority, phrase director,
    # stage perspective 1/3, polyphony ON, no retake noise, ensemble looseness ~= .18.
    assist=1;stage=1;loose=3
    return (assist&3)|(1<<7)|((stage&3)<<19)|(int(bool(multi_out))<<25)|(1<<26)|(1<<27)|((loose&15)<<28)

def _pack_event(e):
    return EVENT.pack(int(e['project_sample']),int(e['type']),int(e['wire_part']),int(e['note']),int(e['articulation']),float(e['velocity']),float(e['tempo_bpm']),*[float(x) for x in e['controls']])

def ping_shadow_v50(host='127.0.0.1',port=49337,timeout=1.0):
    try:
        h=RequestHeader(TYPE_PING,500000,0,0,48000,0,4,1,120.,.35,0)
        with socket.create_connection((host,int(port)),timeout=timeout) as s:
            s.sendall(pack_request_header(h));rh=unpack_response_header(recv_exact(s,RESP_HEADER.size))
        return {'reachable':True,'ready':rh.status==STATUS_OK,'status':rh.status,'flags':rh.flags}
    except Exception as ex:return {'reachable':False,'ready':False,'error':f'{type(ex).__name__}: {ex}'}

def start_shadow_service_v50(host='127.0.0.1',port=49337,mock=False,backend='auto',model_dir=None,cache_dir=None,wait_seconds=25.0):
    status=ping_shadow_v50(host,port)
    if status['reachable']:
        if not status['ready']:raise RuntimeError(f'existing renderer service is reachable but model is not ready: {status}')
        return None,status
    cmd=[sys.executable,'-B',str(Path(__file__).with_name('renderer_service.py')),'--host',host,'--port',str(int(port)),'--backend',backend]
    if mock:cmd.append('--mock')
    if model_dir:cmd+=['--model-dir',str(model_dir)]
    if cache_dir:cmd+=['--cache-dir',str(cache_dir)]
    proc=subprocess.Popen(cmd,cwd=str(Path(__file__).resolve().parent),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    deadline=time.time()+float(wait_seconds);last=None
    while time.time()<deadline:
        if proc.poll() is not None:raise RuntimeError(f'renderer service exited early rc={proc.returncode}')
        last=ping_shadow_v50(host,port,.6)
        if last.get('ready'):return proc,last
        time.sleep(.25)
    try:proc.terminate()
    except Exception:pass
    raise TimeoutError(f'renderer service did not become ready: {last}')

def _render_request(events,start,end,sr,bpm,host,port,request_id,mode=1,flags=None,lookahead=.35,timeout=180.0):
    flags=render_policy_flags_v50(False) if flags is None else int(flags)
    raw=b''.join(_pack_event(e) for e in events)
    h=RequestHeader(TYPE_RENDER,int(request_id),int(start),int(end),int(sr),len(events),4,int(mode),float(bpm),float(lookahead),flags)
    with socket.create_connection((host,int(port)),timeout=5) as s:
        s.settimeout(timeout);s.sendall(pack_request_header(h)+raw)
        rh=unpack_response_header(recv_exact(s,RESP_HEADER.size));payload=recv_exact(s,rh.payload_bytes) if rh.payload_bytes else b''
    if rh.status not in (STATUS_OK,STATUS_CACHE_HIT):raise RuntimeError(f'Shadow render failed status={rh.status}')
    if rh.frames!=(end-start):raise RuntimeError(f'Shadow frame mismatch: {rh.frames} != {end-start}')
    if rh.channels not in (2,24,34):raise RuntimeError(f'unsupported Shadow channel count {rh.channels}')
    x=np.frombuffer(payload,dtype='<f4').reshape(rh.frames,rh.channels).copy()
    if not np.isfinite(x).all():raise RuntimeError('Shadow renderer returned non-finite samples')
    return x[:,:2],rh

def render_midi_v50(midi_path,out_wav=None,host='127.0.0.1',port=49337,sample_rate=48000,chunk_seconds=DEFAULT_CHUNK_SECONDS,overlap_seconds=DEFAULT_OVERLAP_SECONDS,tail_seconds=1.5,request_seed=5000):
    midi_path=Path(midi_path);events,end_sample,bpm=compiled_midi_to_shadow_events_v50(midi_path,sample_rate,tail_seconds)
    chunk=max(5.0,min(44.0,float(chunk_seconds)));over=max(0.0,min(2.0,float(overlap_seconds)))
    chunk_n=int(round(chunk*sample_rate));over_n=int(round(over*sample_rate));step=max(1,chunk_n-over_n)
    starts=list(range(0,end_sample,step));pieces=[]
    for ci,start in enumerate(starts):
        end=min(end_sample,start+chunk_n)
        x,_=_render_request(events,start,end,sample_rate,bpm,host,port,request_seed+ci)
        pieces.append((start,end,x))
        if end>=end_sample:break
    out=np.zeros((end_sample,2),np.float32);weight=np.zeros(end_sample,np.float32)
    for start,end,x in pieces:
        n=end-start;w=np.ones(n,np.float32)
        if over_n>0 and start>0:
            m=min(over_n,n);w[:m]=np.linspace(0,1,m,dtype=np.float32)
        if over_n>0 and end<end_sample:
            m=min(over_n,n);w[-m:]=np.minimum(w[-m:],np.linspace(1,0,m,dtype=np.float32))
        out[start:end]+=x[:n]*w[:,None];weight[start:end]+=w
    nz=weight>1e-7;out[nz]/=weight[nz,None]
    out_wav=Path(out_wav) if out_wav else midi_path.with_suffix('.wav')
    try:
        import soundfile as sf
        sf.write(str(out_wav),out,int(sample_rate),subtype='FLOAT')
    except Exception:
        pcm=(np.clip(out,-1,1)*32767.).astype('<i2')
        with wave.open(str(out_wav),'wb') as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(int(sample_rate));w.writeframes(pcm.tobytes())
    return {'wav':out_wav,'frames':end_sample,'sample_rate':int(sample_rate),'chunks':len(pieces),'peak':float(np.max(np.abs(out))) if out.size else 0.0,'events':len(events)}

def main(argv=None):
    ap=argparse.ArgumentParser(description='Render a SONICRAFT compiled Strings MIDI through the local Shadow Renderer service.')
    ap.add_argument('midi',type=Path);ap.add_argument('-o','--out',type=Path);ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=49337)
    ap.add_argument('--mock',action='store_true');ap.add_argument('--backend',choices=['auto','torch','ort'],default='auto');ap.add_argument('--model-dir',type=Path);ap.add_argument('--cache-dir',type=Path)
    a=ap.parse_args(argv);proc=None
    try:
        proc,status=start_shadow_service_v50(a.host,a.port,a.mock,a.backend,a.model_dir,a.cache_dir)
        r=render_midi_v50(a.midi,a.out,a.host,a.port)
        print('SONICRAFT v5.0 Local Shadow Render OK',r)
        return 0
    except Exception as ex:
        print('ERROR:',ex,file=sys.stderr);return 2
    finally:
        if proc is not None:
            try:proc.terminate();proc.wait(timeout=3)
            except Exception:
                try:proc.kill()
                except Exception:pass
if __name__=='__main__':raise SystemExit(main())
