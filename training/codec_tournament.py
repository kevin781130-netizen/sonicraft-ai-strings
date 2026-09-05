from __future__ import annotations
"""Codec reconstruction tournament for SONICRAFT v1.9.

The tournament is deliberately codec-agnostic. Candidate reconstructions can be
produced by SONICRAFT VAE64, ACE-Step/Oobleck, DAC or any future legal challenger.
This avoids shipping third-party training stacks just to compare them.

Winner selection is quality-first. Only candidates inside a small quality tie
window are allowed to win on lower latent state / decoder bytes.
"""
from pathlib import Path
from typing import Mapping, Sequence
import json, math
import numpy as np
import soundfile as sf

TOURNAMENT_SCHEMA = 1


def _mono(path: str | Path) -> tuple[np.ndarray, int]:
    x, sr = sf.read(path, dtype='float32', always_2d=True)
    return np.asarray(x, np.float32).mean(1), int(sr)


def _resample_linear(x: np.ndarray, sr: int, target: int) -> np.ndarray:
    if sr == target or x.size < 2: return x
    n = max(1, int(round(x.size * target / sr)))
    old = np.linspace(0.0, 1.0, x.size, endpoint=False)
    new = np.linspace(0.0, 1.0, n, endpoint=False)
    return np.interp(new, old, x).astype(np.float32)


def _frame(x: np.ndarray, n: int, hop: int) -> np.ndarray:
    if x.size < n: x=np.pad(x,(0,n-x.size))
    count=max(1,1+(x.size-n)//hop)
    return np.stack([x[i*hop:i*hop+n] for i in range(count)],0)


def _stft_mag(x: np.ndarray, n: int, hop: int) -> np.ndarray:
    f=_frame(x,n,hop)*np.hanning(n)[None,:]
    return np.abs(np.fft.rfft(f,axis=1)).astype(np.float64)+1e-9


def _mr_spectral_error(ref: np.ndarray, rec: np.ndarray) -> tuple[float,float]:
    conv=[]; logs=[]
    for n,hop in ((256,64),(512,128),(1024,256),(2048,512)):
        a=_stft_mag(ref,n,hop); b=_stft_mag(rec,n,hop); k=min(len(a),len(b)); a=a[:k]; b=b[:k]
        conv.append(float(np.linalg.norm(a-b)/(np.linalg.norm(a)+1e-12)))
        logs.append(float(np.mean(np.abs(np.log(a)-np.log(b)))))
    return float(np.mean(conv)), float(np.mean(logs))


def _si_sdr(ref: np.ndarray, rec: np.ndarray) -> float:
    ref=ref-ref.mean(); rec=rec-rec.mean(); den=float(np.dot(ref,ref))+1e-12
    scale=float(np.dot(rec,ref))/den; target=scale*ref; noise=rec-target
    return float(10*np.log10((np.dot(target,target)+1e-12)/(np.dot(noise,noise)+1e-12)))


def _envelope_corr(ref: np.ndarray, rec: np.ndarray) -> float:
    def env(x):
        fr=_frame(x,1024,256); return np.sqrt(np.mean(fr*fr,axis=1)+1e-12)
    a,b=env(ref),env(rec); k=min(a.size,b.size); a=a[:k];b=b[:k]
    if k<2 or np.std(a)<1e-9 or np.std(b)<1e-9: return 1.0 if np.allclose(a,b,atol=1e-6) else 0.0
    return float(np.clip(np.corrcoef(a,b)[0,1],-1,1))


def _flux_error(ref: np.ndarray, rec: np.ndarray) -> float:
    def flux(x):
        m=_stft_mag(x,512,128); m=m/(m.sum(1,keepdims=True)+1e-12); d=np.maximum(0,m[1:]-m[:-1]); return d.sum(1)
    a,b=flux(ref),flux(rec); k=min(a.size,b.size)
    if k==0:return 0.0
    scale=max(float(np.mean(np.abs(a)))+1e-9,1e-6)
    return float(np.mean(np.abs(a[:k]-b[:k]))/scale)


def _band_energy_error(ref: np.ndarray, rec: np.ndarray, sr:int) -> float:
    n=1<<int(math.floor(math.log2(max(64,min(len(ref),len(rec),131072)))))
    a=np.abs(np.fft.rfft(ref[:n]*np.hanning(n)))**2; b=np.abs(np.fft.rfft(rec[:n]*np.hanning(n)))**2
    f=np.fft.rfftfreq(n,1/sr); bands=((40,400),(400,2000),(2000,8000),(8000,min(20000,sr/2)))
    errs=[]
    for lo,hi in bands:
        mask=(f>=lo)&(f<hi)
        if not np.any(mask):continue
        ea=float(a[mask].sum())+1e-12; eb=float(b[mask].sum())+1e-12
        errs.append(abs(10*math.log10(eb/ea)))
    return float(np.mean(errs)) if errs else 0.0


def compare_pair(reference: str|Path, reconstruction: str|Path) -> dict:
    ref,sr=_mono(reference); rec,rsr=_mono(reconstruction)
    if rsr!=sr: rec=_resample_linear(rec,rsr,sr)
    n=min(len(ref),len(rec)); ref=ref[:n];rec=rec[:n]
    if n<256: raise ValueError('codec pair is too short')
    sc,log=_mr_spectral_error(ref,rec); sisdr=_si_sdr(ref,rec); env=_envelope_corr(ref,rec); flux=_flux_error(ref,rec); band=_band_energy_error(ref,rec,sr)
    # Bounded components. Identity reaches ~100; severe distortion approaches 0.
    spectral=100*math.exp(-2.5*sc-0.18*log)
    sdr=100/(1+math.exp(-(sisdr-12.0)/4.0))
    envelope=100*max(0.0,(env+1.0)/2.0)
    transient=100*math.exp(-1.8*max(0.0,flux))
    bands=100*math.exp(-0.12*max(0.0,band))
    score=.38*spectral+.24*sdr+.16*envelope+.14*transient+.08*bands
    return {'sample_rate':sr,'samples':n,'mr_spectral_convergence':sc,'log_spectral_distance':log,
            'si_sdr_db':sisdr,'envelope_corr':env,'transient_flux_error':flux,'band_energy_error_db':band,
            'quality_score':float(np.clip(score,0,100))}


def load_pairs(path: str|Path) -> list[dict]:
    out=[]
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if line.strip():out.append(json.loads(line))
    return out


def run_tournament(rows: Sequence[Mapping], *, min_quality:float=80.0, tie_window:float=.50) -> dict:
    grouped={}
    for row in rows:
        cid=str(row.get('candidate_id') or row.get('candidate') or '').strip()
        if not cid: raise ValueError('pair row missing candidate_id')
        origin=str(row.get('training_origin','real')).lower()
        metrics=compare_pair(row['reference'],row['reconstruction'])
        e=grouped.setdefault(cid,{'candidate_id':cid,'kind':str(row.get('kind') or cid),'latent_ch':row.get('latent_ch'),
                                  'latent_hz':row.get('latent_hz'),'decoder_bytes':row.get('decoder_bytes'),
                                  'real':[],'modeled':[]})
        e['modeled' if origin in ('modeled','synthetic','physics','cleanroom') else 'real'].append(metrics)
    candidates=[]
    for cid,e in grouped.items():
        if not e['real']: continue
        scores=[x['quality_score'] for x in e['real']]
        agg=dict(e); agg['real_anchor_count']=len(scores); agg['modeled_diagnostic_count']=len(e['modeled'])
        agg['real_quality_mean']=float(np.mean(scores)); agg['real_quality_p10']=float(np.percentile(scores,10))
        agg['real_si_sdr_mean_db']=float(np.mean([x['si_sdr_db'] for x in e['real']]))
        agg['real_spectral_convergence_mean']=float(np.mean([x['mr_spectral_convergence'] for x in e['real']]))
        agg['latent_scalars_per_sec']=(float(e['latent_ch'])*float(e['latent_hz'])) if e.get('latent_ch') is not None and e.get('latent_hz') is not None else None
        candidates.append(agg)
    if not candidates:
        return {'schema':TOURNAMENT_SCHEMA,'release_pass':False,'promotion_pass':False,'reason':'no real-anchor codec pairs','candidates':[]}
    best_quality=max(c['real_quality_mean'] for c in candidates)
    tied=[c for c in candidates if c['real_quality_mean']>=best_quality-tie_window]
    # Within perceptually-near quality, prefer smaller temporal state, then smaller decoder.
    def efficiency_key(c):
        l=c.get('latent_scalars_per_sec'); b=c.get('decoder_bytes')
        return (float('inf') if l is None else l,float('inf') if b is None else float(b),-c['real_quality_mean'])
    winner=min(tied,key=efficiency_key)
    promotion=bool(winner['real_quality_mean']>=min_quality and winner['real_quality_p10']>=min_quality-8.0)
    compact=[]
    for c in sorted(candidates,key=lambda x:x['real_quality_mean'],reverse=True):
        cc={k:v for k,v in c.items() if k not in ('real','modeled')}; compact.append(cc)
    return {'schema':TOURNAMENT_SCHEMA,'release_pass':promotion,'promotion_pass':promotion,'quality_first':True,
            'quality_tie_window':tie_window,'min_quality':min_quality,'winner':winner['candidate_id'],'winner_kind':winner['kind'],
            'real_anchor_count':winner['real_anchor_count'],'winner_quality':winner['real_quality_mean'],
            'candidates':compact,'notes':'Modeled rows are diagnostics only and never select the timbre codec winner.'}
