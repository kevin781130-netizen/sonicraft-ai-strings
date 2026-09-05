from __future__ import annotations
"""Analyze RIGHTS-CLEARED real string recordings into conservative physical supervision.

This is intentionally an analyzer, not a rights oracle. Every row must already pass the
commercial source registry. Per-file sources (MusicNet/Commons/FSD) should be audited first.

Supported rows:
  {"audio":"...wav", "dataset":"...", "control_npz":"optional aligned controls.npz"}
Or a single-note row with `midi_note`, as emitted by Good-sounds manifests.

Outputs contain F0/RMS/spectral features, per-output vibrato masks, and conservative
bow-change markers. Legato/Portamento timing is derived later by derive_performance_physics.py
when true note onsets + intended pitch are available.
"""
import argparse,json,math,hashlib
from pathlib import Path
import numpy as np
import soundfile as sf
import torch, torchaudio
try:
    import librosa
except Exception:
    librosa=None

import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_policy import assert_commercial_sources

DYN={'ppp':.18,'pp':.26,'p':.34,'mp':.46,'mf':.60,'f':.74,'ff':.86,'fff':.94}
INST={'violin':0,'vln':0,'viola':1,'cello':2,'violoncello':2}

def _interp(x,n):
    x=np.asarray(x,float).reshape(-1)
    if len(x)==n:return x.astype(np.float32)
    if len(x)<2:return np.full(n,float(x[0]) if len(x) else 0,np.float32)
    return np.interp(np.linspace(0,1,n),np.linspace(0,1,len(x)),x).astype(np.float32)

def _audio_features(path,fps=100):
    wav,sr=sf.read(path,dtype='float32',always_2d=True); x=torch.from_numpy(wav.T).mean(0,keepdim=True)
    if sr!=16000: x=torchaudio.functional.resample(x,sr,16000);sr=16000
    if x.shape[-1] < sr//3: raise RuntimeError('audio too short for performance analysis')
    frame_time=1.0/fps
    hop=max(1,int(round(sr/fps)))
    if librosa is not None:
        # YIN is deterministic, model-free and far more stable than coarse autocorrelation
        # on sustained bowed-string pitch modulation. It is a training/offline dependency only.
        f0=librosa.yin(x[0].cpu().numpy(),fmin=45,fmax=1900,sr=sr,frame_length=1024,hop_length=hop)
    else:
        f0=torchaudio.functional.detect_pitch_frequency(x,sr,frame_time=frame_time,win_length=25,freq_low=45,freq_high=1900)[0].cpu().numpy()
    nfft=1024; win=torch.hann_window(nfft)
    S=torch.stft(x[0],n_fft=nfft,hop_length=hop,win_length=nfft,window=win,return_complex=True,center=True).abs()
    power=S.pow(2);freq=torch.linspace(0,sr/2,S.shape[0])[:,None]
    centroid=((power*freq).sum(0)/(power.sum(0)+1e-9)).cpu().numpy()
    rms=torch.sqrt(torch.nn.functional.avg_pool1d(x.pow(2).unsqueeze(0),kernel_size=hop*2+1,stride=hop,padding=hop).squeeze()+1e-9).cpu().numpy()
    logS=torch.log1p(S); flux=torch.relu(logS[:,1:]-logS[:,:-1]).mean(0);flux=torch.cat([flux[:1],flux]).cpu().numpy()
    n=max(len(f0),len(centroid),len(rms),len(flux));
    f0=_interp(f0,n);centroid=_interp(centroid,n);rms=_interp(rms,n);flux=_interp(flux,n)
    f0m=np.where(f0>1,69+12*np.log2(np.maximum(f0,1e-6)/440.0),np.nan).astype(np.float32)
    clip=float((np.abs(wav)>=.999).mean()); peak=float(np.max(np.abs(wav)))
    return {'f0_midi':f0m,'rms':rms,'spectral_centroid':centroid,'spectral_flux':flux,
            'fps':np.array(float(fps),np.float32),'audio_peak':np.array(peak,np.float32),'clip_fraction':np.array(clip,np.float32)}

def _instrument(row):
    s=str(row.get('instrument','violin')).lower()
    for k,v in INST.items():
        if k in s:return v
    return 0

def _single_note_controls(row,n,fps):
    p=float(row.get('midi_note',69) or 69); bpm=float(row.get('tempo_bpm',68) or 68);inst=_instrument(row)
    dyn=row.get('dynamic') or row.get('dynamics') or 'mf'
    try: dv=float(dyn); dv=dv/127.0 if dv>1 else dv
    except Exception: dv=DYN.get(str(dyn).lower(),.60)
    gate=np.ones(n,np.float32);on=np.zeros(n,np.float32);on[0]=1
    progress=np.linspace(0,1,n,dtype=np.float32);durbeats=(n/fps)*bpm/60.0
    return {'pitch':np.full(n,p,np.float32),'gate':gate,'onset':on,'velocity':np.full(n,.72,np.float32),
            'dynamics':np.full(n,dv,np.float32),'vibrato':np.zeros(n,np.float32),'expression':np.full(n,.90,np.float32),
            'legato':np.zeros(n,np.float32),'pitchbend':np.zeros(n,np.float32),'transition_speed':np.full(n,.5,np.float32),
            'short_tightness':np.full(n,.5,np.float32),'attack_character':np.full(n,.38,np.float32),'speed_profile':np.zeros(n,np.float32),
            'tempo_bpm':np.full(n,bpm,np.float32),'note_duration_beats':np.full(n,durbeats,np.float32),
            'note_progress':progress,'phrase_position':progress.copy(),'prev_interval':np.zeros(n,np.float32),'next_interval':np.zeros(n,np.float32),
            'articulation_curve':np.zeros(n,np.float32),'instrument':np.array(inst,np.int64)}

def _load_controls(row,n,fps):
    cp=row.get('control_npz') or row.get('aligned_npz')
    if cp and Path(cp).exists():
        d=np.load(cp);keys={k:d[k] for k in d.files};m=len(np.asarray(keys['pitch']))
        # analysis features will be resampled to the control frame count
        keys.setdefault('instrument',np.array(_instrument(row),np.int64));return keys,m
    if row.get('midi_note') is not None:
        return _single_note_controls(row,n,fps),n
    return None,n

def _runs_from_onset(keys,n):
    on=np.asarray(keys.get('onset',np.zeros(n)),float)>.5; gate=np.asarray(keys.get('gate',np.ones(n)),float)>.2
    idx=np.flatnonzero(on)
    if not len(idx): idx=np.array([0],int)
    for ii,a in enumerate(idx):
        b=int(idx[ii+1]) if ii+1<len(idx) else n
        off=np.flatnonzero(~gate[a:b])
        if len(off):b=min(b,a+int(off[0]))
        if b>a+3:yield int(a),int(b)

def _vibrato(keys,f0m,fps):
    n=len(f0m); out={k:np.zeros(n,np.float32) for k in ('vibrato_depth_cents','vibrato_rate_hz','vibrato_onset_ms','vibrato_jitter','vibrato_confidence','vibrato_detected','vibrato_known','vibrato_depth_known','vibrato_rate_known','vibrato_onset_known','vibrato_jitter_known')}
    pitch=np.asarray(keys.get('pitch',np.full(n,np.nan)),float)
    for a,b in _runs_from_onset(keys,n):
        if b-a < int(.42*fps): continue
        # Avoid the attack and release for physical vibrato estimation.
        aa=min(b-1,a+int(.09*fps));bb=max(aa+4,b-int(.07*fps));f=np.asarray(f0m[aa:bb],float);base=np.asarray(pitch[aa:bb],float)
        valid=np.isfinite(f)&np.isfinite(base)&(np.abs(f-base)<2.5)
        voiced=float(valid.mean()) if len(valid) else 0
        if voiced<.62:continue
        cents=(f-base)*100.0;good=cents.copy();
        # Interpolate unvoiced holes before detrending.
        ids=np.arange(len(good));vg=np.isfinite(good)&valid
        if vg.sum()<8:continue
        good[~vg]=np.interp(ids[~vg],ids[vg],good[vg])
        win=max(5,int(round(.38*fps)));kernel=np.ones(win,np.float32)/win;trend=np.convolve(good,kernel,mode='same');res=good-trend
        core=res[max(1,win//2):max(win//2+2,len(res)-win//2)]
        if len(core)<8:core=res
        depth=float(.5*(np.percentile(core,95)-np.percentile(core,5)))
        y=core-core.mean();freq=np.fft.rfftfreq(len(y),d=1.0/fps);pow=np.abs(np.fft.rfft(y))**2;band=(freq>=3.5)&(freq<=8.5)
        periodic=0.;rate=0.
        if band.any() and pow[band].sum()>1e-8:
            inds=np.where(band)[0];pi=inds[int(np.argmax(pow[band]))];rate=float(freq[pi]);periodic=float(pow[pi]/(pow[band].sum()+1e-9))
        stable=depth<4.5 and float(np.nanstd(core))<5.0
        detected=depth>=4.5 and 3.7<=rate<=8.2 and periodic>=.14
        conf=float(np.clip((voiced-.55)*1.3 + periodic*.9 + (.18 if detected or stable else 0),0,1))
        if not (detected or stable) or conf<.52:continue
        out['vibrato_depth_cents'][a:b]=float(np.clip(depth if detected else 0,0,90));out['vibrato_depth_known'][a:b]=1;out['vibrato_confidence'][a:b]=conf;out['vibrato_detected'][a:b]=1 if detected else 0
        if detected:
            out['vibrato_rate_hz'][a:b]=rate;out['vibrato_rate_known'][a:b]=1;out['vibrato_known'][a:b]=1
            # onset: first sustained local std rise after attack, not the first individual cycle.
            threshold=max(3.0,.28*depth);local=[];rw=max(3,int(.10*fps))
            full=res
            for j in range(len(full)):
                l=max(0,j-rw);r=min(len(full),j+rw+1);local.append(float(np.std(full[l:r])))
            local=np.asarray(local);candidates=np.flatnonzero((local>threshold)&(np.arange(len(local))>=int(.04*fps)))
            onset_ms=float((candidates[0]/fps)*1000.0) if len(candidates) else 220.0
            onset_ms=float(np.clip(onset_ms,30,900));out['vibrato_onset_ms'][a:b]=onset_ms;out['vibrato_onset_known'][a:b]=1
            # normalized half-cycle irregularity proxy
            jitter=float(np.clip(np.std(np.diff(core))/max(5.0,depth)/5.0,0,.12));out['vibrato_jitter'][a:b]=jitter;out['vibrato_jitter_known'][a:b]=1
    return out

def _bow_markers(keys,feat,fps):
    n=len(feat['rms']);flux=np.asarray(feat['spectral_flux'],float);rms=np.asarray(feat['rms'],float);f0=np.asarray(feat['f0_midi'],float)
    on=np.asarray(keys.get('onset',np.zeros(n)),float)>.5
    med=float(np.median(flux));mad=float(np.median(np.abs(flux-med)))+1e-8;thr=med+4.5*mad
    cand=np.flatnonzero(flux>thr);mark=np.zeros(n,np.float32);last=-10**9
    for j in cand:
        if j-last<int(.22*fps) or j<int(.16*fps) or j>=n-int(.10*fps):continue
        if on[max(0,j-int(.13*fps)):min(n,j+int(.13*fps))].any():continue
        r=max(2,int(.055*fps));a=j-r;b=j+r+1
        loc=rms[a:b];base=float(np.median(loc))+1e-8;dip=(base-float(np.min(loc)))/base
        left=np.nanmedian(f0[max(0,j-r):j]);right=np.nanmedian(f0[j:min(n,j+r)])
        if not np.isfinite(left+right) or abs(left-right)*100>24:continue
        if dip<.07:continue
        mark[j]=1;last=j
    return mark

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--out-dir',required=True);ap.add_argument('--out-index',required=True)
    ap.add_argument('--registry',default='training/dataset_registry.json');ap.add_argument('--fps',type=int,default=100);a=ap.parse_args()
    rows=[json.loads(x) for x in Path(a.manifest).read_text(encoding='utf-8').splitlines() if x.strip()]
    assert_commercial_sources([r.get('dataset') or r.get('dataset_id') for r in rows],a.registry)
    od=Path(a.out_dir);od.mkdir(parents=True,exist_ok=True);out=[]
    for ri,r in enumerate(rows):
        audio=Path(r.get('audio') or '');
        if not audio.exists(): continue
        feat=_audio_features(str(audio),a.fps);raw_n=len(feat['f0_midi']);keys,target_n=_load_controls(r,raw_n,a.fps)
        if keys is None:
            # Acoustic-only rows are intentionally not converted into expert supervision.
            continue
        feat={k:(_interp(v,target_n) if isinstance(v,np.ndarray) and v.ndim==1 and len(v)>1 else v) for k,v in feat.items()}
        # Resample control arrays only when needed; scalar instrument/fps remain scalar.
        norm={}
        for k,v in keys.items():
            ar=np.asarray(v)
            norm[k]=_interp(ar,target_n) if ar.ndim==1 and len(ar)>1 and len(ar)!=target_n else ar
        norm.update(feat);norm['bow_change_marker']=_bow_markers(norm,feat,a.fps);norm.update(_vibrato(norm,np.asarray(feat['f0_midi']),a.fps));norm['fps']=np.array(float(a.fps),np.float32)
        dst=od/(f'{ri:06d}_'+audio.stem+'_real_v08.npz');np.savez_compressed(dst,**norm)
        rr=dict(r);rr['file']=str(dst);rr['analysis']='real_performance_v08';rr['audio_sha256']=hashlib.sha256(audio.read_bytes()).hexdigest();out.append(rr)
    p=Path(a.out_index);p.parent.mkdir(parents=True,exist_ok=True);p.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf-8')
    print('real aligned/analyzable rows',len(out),'->',p)
if __name__=='__main__':main()
