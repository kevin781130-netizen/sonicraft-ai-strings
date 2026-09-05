from __future__ import annotations
"""String-section codec tournament with stereo/phase-aware quality-first scoring."""
from pathlib import Path
from typing import Mapping, Sequence
import math, numpy as np, soundfile as sf
from codec_tournament import _frame, _stft_mag, _mr_spectral_error, _si_sdr, _envelope_corr, _flux_error, _band_energy_error

TOURNAMENT_SCHEMA=2


def _audio(path):
    x,sr=sf.read(path,dtype='float32',always_2d=True);return np.asarray(x,np.float32),int(sr)

def _resample(x,sr,target):
    if sr==target:return x
    n=max(1,int(round(len(x)*target/sr))); old=np.linspace(0,1,len(x),endpoint=False);new=np.linspace(0,1,n,endpoint=False)
    return np.stack([np.interp(new,old,x[:,c]) for c in range(x.shape[1])],1).astype(np.float32)

def _channels(x,n=2):
    if x.shape[1]==n:return x
    if x.shape[1]==1 and n==2:return np.repeat(x,2,1)
    return x[:,:n]

def _corr_lr(x):
    if x.shape[1]<2:return 1.0
    a=x[:,0]-x[:,0].mean();b=x[:,1]-x[:,1].mean();den=np.linalg.norm(a)*np.linalg.norm(b)
    return float(np.dot(a,b)/den) if den>1e-12 else 1.0

def _side_ratio_db(x):
    if x.shape[1]<2:return -120.0
    m=(x[:,0]+x[:,1])*.5;s=(x[:,0]-x[:,1])*.5
    return float(10*np.log10((np.mean(s*s)+1e-12)/(np.mean(m*m)+1e-12)))

def _phase_derivative_error(ref,rec,n=1024,hop=256):
    # Independent implementation: compare wrapped inter-frame (IF proxy) and inter-bin (GD proxy) phase derivatives.
    def spec(x):
        fr=_frame(x,n,hop)*np.hanning(n)[None,:];return np.fft.rfft(fr,axis=1)
    errs=[]
    for c in range(min(ref.shape[1],rec.shape[1])):
        A=spec(ref[:,c]);B=spec(rec[:,c]);k=min(len(A),len(B));A=A[:k];B=B[:k]
        if k<2:continue
        mag=np.abs(A);w=mag/(mag.mean()+1e-9);pa=np.angle(A);pb=np.angle(B)
        wrap=lambda z: np.angle(np.exp(1j*z))
        ife=np.mean(np.abs(wrap(np.diff(pa,axis=0)-np.diff(pb,axis=0)))*w[1:])/(np.mean(w[1:])+1e-9)
        gde=np.mean(np.abs(wrap(np.diff(pa,axis=1)-np.diff(pb,axis=1)))*w[:,:-1])/(np.mean(w[:,:-1])+1e-9)
        errs.append(float(.5*(ife+gde)))
    return float(np.mean(errs)) if errs else 0.0

def _harmonic_texture_error(ref,rec,sr):
    # String-oriented high-harmonic texture metric without requiring an F0 model.
    mono=lambda x:np.asarray(x,np.float32).mean(1)
    a=mono(ref);b=mono(rec);n=2048;hop=512;A=_stft_mag(a,n,hop);B=_stft_mag(b,n,hop);k=min(len(A),len(B));A=A[:k];B=B[:k]
    f=np.fft.rfftfreq(n,1/sr);mask=(f>=180)&(f<=14000)
    if not np.any(mask):return 0.0
    # log-spectral derivative emphasizes harmonic ridge/valley texture rather than absolute level.
    la=np.log(A[:,mask]+1e-8);lb=np.log(B[:,mask]+1e-8)
    da=np.diff(la,axis=1);db=np.diff(lb,axis=1)
    return float(np.mean(np.abs(da-db)))

def compare_pair_v20(reference,reconstruction):
    ref,sr=_audio(reference);rec,rsr=_audio(reconstruction);rec=_resample(rec,rsr,sr);ref=_channels(ref);rec=_channels(rec)
    n=min(len(ref),len(rec));ref=ref[:n];rec=rec[:n]
    if n<512:raise ValueError('codec pair is too short')
    rm=ref.mean(1);cm=rec.mean(1);sc,log=_mr_spectral_error(rm,cm);sisdr=_si_sdr(rm,cm);env=_envelope_corr(rm,cm);flux=_flux_error(rm,cm);band=_band_energy_error(rm,cm,sr)
    corr_err=abs(_corr_lr(ref)-_corr_lr(rec));width_err=abs(_side_ratio_db(ref)-_side_ratio_db(rec));phase=_phase_derivative_error(ref,rec);harm=_harmonic_texture_error(ref,rec,sr)
    spectral=100*math.exp(-2.35*sc-.16*log);sdr=100/(1+math.exp(-(sisdr-12)/4));envelope=100*max(0,(env+1)/2)
    transient=100*math.exp(-1.7*max(0,flux));bands=100*math.exp(-.11*max(0,band));stereo=100*math.exp(-2.8*corr_err-.12*width_err)
    phase_s=100*math.exp(-.9*phase);harm_s=100*math.exp(-.45*harm)
    score=.28*spectral+.18*sdr+.11*envelope+.11*transient+.07*bands+.10*stereo+.08*phase_s+.07*harm_s
    return {'sample_rate':sr,'samples':n,'mr_spectral_convergence':sc,'log_spectral_distance':log,'si_sdr_db':sisdr,'envelope_corr':env,
            'transient_flux_error':flux,'band_energy_error_db':band,'stereo_corr_error':corr_err,'stereo_width_error_db':width_err,
            'phase_derivative_error':phase,'harmonic_texture_error':harm,'quality_score':float(np.clip(score,0,100))}

def run_tournament_v20(rows:Sequence[Mapping],*,min_quality=82.0,tie_window=.40,min_real_anchors=8):
    grouped={}
    for row in rows:
        cid=str(row.get('candidate_id') or row.get('candidate') or '').strip();
        if not cid:raise ValueError('pair row missing candidate_id')
        origin=str(row.get('training_origin','real')).lower();metrics=compare_pair_v20(row['reference'],row['reconstruction'])
        e=grouped.setdefault(cid,{'candidate_id':cid,'kind':str(row.get('kind') or cid),'latent_ch':row.get('latent_ch'),'latent_hz':row.get('latent_hz'),
                                  'decoder_bytes':row.get('decoder_bytes'),'real':[],'modeled':[]})
        e['modeled' if origin in ('modeled','synthetic','physics','cleanroom') else 'real'].append(metrics)
    candidates=[]
    for e in grouped.values():
        if not e['real']:continue
        s=np.asarray([x['quality_score'] for x in e['real']],np.float64);agg={k:v for k,v in e.items() if k not in ('real','modeled')}
        agg.update({'real_anchor_count':len(s),'modeled_diagnostic_count':len(e['modeled']),'real_quality_mean':float(s.mean()),'real_quality_p10':float(np.percentile(s,10)),
                    'real_stereo_corr_error_mean':float(np.mean([x['stereo_corr_error'] for x in e['real']])),
                    'real_phase_derivative_error_mean':float(np.mean([x['phase_derivative_error'] for x in e['real']])),
                    'real_harmonic_texture_error_mean':float(np.mean([x['harmonic_texture_error'] for x in e['real']]))})
        agg['latent_scalars_per_sec']=float(e['latent_ch'])*float(e['latent_hz']) if e.get('latent_ch') is not None and e.get('latent_hz') is not None else None;candidates.append(agg)
    if not candidates:return {'schema':2,'promotion_pass':False,'release_pass':False,'reason':'no real-anchor codec pairs','candidates':[]}
    best=max(c['real_quality_mean'] for c in candidates);tied=[c for c in candidates if c['real_quality_mean']>=best-tie_window]
    def eff(c):return (float('inf') if c.get('latent_scalars_per_sec') is None else c['latent_scalars_per_sec'],float('inf') if c.get('decoder_bytes') is None else c['decoder_bytes'],-c['real_quality_mean'])
    winner=min(tied,key=eff);promotion=winner['real_anchor_count']>=min_real_anchors and winner['real_quality_mean']>=min_quality and winner['real_quality_p10']>=min_quality-7
    return {'schema':2,'metric_family':'stereo_phase_harmonic_strings_v20','quality_first':True,'quality_tie_window':tie_window,'min_quality':min_quality,
            'min_real_anchors':min_real_anchors,'promotion_pass':bool(promotion),'release_pass':bool(promotion),'winner':winner['candidate_id'],'winner_kind':winner['kind'],
            'winner_quality':winner['real_quality_mean'],'real_anchor_count':winner['real_anchor_count'],'candidates':sorted(candidates,key=lambda x:x['real_quality_mean'],reverse=True),
            'notes':'Real rows select the codec. Modeled rows remain diagnostics. Stereo/phase/harmonic preservation are explicit.'}
