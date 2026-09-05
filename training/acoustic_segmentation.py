from __future__ import annotations
"""SONICRAFT v2.0 Acoustic Promotion: deterministic phrase segmentation.

The segmenter is intentionally dependency-light and score-authoritative:
- it never changes dataset rights/origin metadata;
- it only cuts rows already admitted by Sound Forge;
- cuts prefer sustained low-energy valleys and avoid very short fragments;
- output rows preserve original SHA/provenance so later codec/ABX evidence is traceable.
"""
from pathlib import Path
from typing import Mapping, Sequence
import hashlib, json, math
import numpy as np
import soundfile as sf

SEGMENT_SCHEMA=1
SEGMENT_VERSION='acoustic_segments_v20'


def _sha_bytes(x: bytes) -> str:
    return hashlib.sha256(x).hexdigest()


def _frame_features(x: np.ndarray, sr: int, frame_ms: float=40.0, hop_ms: float=20.0):
    mono=np.asarray(x,np.float32).mean(1) if x.ndim==2 else np.asarray(x,np.float32).reshape(-1)
    n=max(64,int(round(sr*frame_ms/1000.0))); hop=max(32,int(round(sr*hop_ms/1000.0)))
    if mono.size<n: mono=np.pad(mono,(0,n-mono.size))
    count=max(1,1+(mono.size-n)//hop); win=np.hanning(n).astype(np.float32)
    rms=np.empty(count,np.float32); flux=np.zeros(count,np.float32); prev=None
    for i in range(count):
        s=mono[i*hop:i*hop+n]; rms[i]=np.sqrt(np.mean(s*s)+1e-12)
        mag=np.abs(np.fft.rfft(s*win)).astype(np.float32); mag/=float(mag.sum()+1e-12)
        if prev is not None: flux[i]=float(np.maximum(mag-prev,0).sum())
        prev=mag
    db=20*np.log10(np.maximum(rms,1e-12)); return db,flux,n,hop


def segment_boundaries(audio: np.ndarray, sr: int, *, min_sec:float=1.5, target_sec:float=6.0,
                       max_sec:float=10.0, silence_rel_db:float=32.0) -> list[tuple[int,int,str]]:
    """Return sample boundaries. Prefer silence valleys; force max length if needed."""
    frames=len(audio); duration=frames/max(1,sr)
    if duration<=max_sec: return [(0,frames,'whole')]
    db,flux,_,hop=_frame_features(audio,sr); active=db[np.isfinite(db)]
    ref=float(np.percentile(active,90)) if active.size else -20.0; threshold=max(-70.0,ref-silence_rel_db)
    quiet=db<=threshold
    # Candidate valley centers; require >= ~80 ms quiet to avoid cutting bow texture dips.
    qrun=max(2,int(round(.08*sr/hop))); candidates=[]; i=0
    while i<len(quiet):
        if not quiet[i]: i+=1; continue
        j=i
        while j<len(quiet) and quiet[j]: j+=1
        if j-i>=qrun:
            k=(i+j-1)//2; candidates.append(int(k*hop))
        i=j
    out=[]; start=0; min_n=int(min_sec*sr); target_n=int(target_sec*sr); max_n=int(max_sec*sr)
    while frames-start>max_n:
        lo=start+min_n; hi=min(frames,start+max_n); target=min(frames,start+target_n)
        viable=[c for c in candidates if lo<=c<=hi]
        if viable:
            # Distance to target dominates; spectral-flux valley is tie breaker.
            def key(c):
                fi=min(len(flux)-1,max(0,int(c/hop)))
                return (abs(c-target),float(flux[fi]))
            cut=min(viable,key=key); reason='silence_valley'
        else:
            # Forced cut chooses the lowest-energy frame around target..max, not blindly max_sec.
            a=max(0,int(lo/hop)); b=min(len(db)-1,int(hi/hop)); t=max(a,min(b,int(target/hop)))
            idx=min(range(a,b+1),key=lambda z:(float(db[z]),abs(z-t))) if b>=a else t
            cut=max(lo,min(hi,int(idx*hop))); reason='energy_valley_forced'
        if cut-start<min_n: cut=min(frames,start+max_n); reason='max_forced'
        out.append((start,cut,reason)); start=cut
    if frames-start>=min_n or not out: out.append((start,frames,'tail'))
    else:
        a,b,r=out[-1];out[-1]=(a,frames,r+'+short_tail_merge')
    return out


def segment_forged_rows(rows: Sequence[Mapping], out_dir: str|Path, *, min_sec=1.5,target_sec=6.0,max_sec=10.0) -> tuple[list[dict],dict]:
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True); seg_rows=[]; rejected=0
    for ri,row0 in enumerate(rows):
        row=dict(row0)
        if not row.get('forge_release_eligible'):
            rejected+=1;continue
        src=Path(row.get('audio') or row.get('path') or row.get('file'))
        x,sr=sf.read(src,dtype='float32',always_2d=True)
        for si,(a,b,reason) in enumerate(segment_boundaries(x,sr,min_sec=min_sec,target_sec=target_sec,max_sec=max_sec)):
            y=x[a:b]; ext='.wav'; origin=str(row.get('training_origin','real')).lower()
            digest=(row.get('forge_sha256') or _sha_bytes(src.read_bytes()))[:16]
            name=f'{origin}_{digest}_{ri:06d}_{si:03d}{ext}'; dst=out/name
            sf.write(dst,y,sr,subtype='FLOAT')
            nr=dict(row); nr.update({
                'audio':str(dst),'segment_schema':SEGMENT_SCHEMA,'segment_version':SEGMENT_VERSION,
                'segment_parent_audio':str(src),'segment_parent_sha256':row.get('forge_sha256'),
                'segment_index':si,'segment_start_sample':int(a),'segment_end_sample':int(b),
                'segment_start_sec':a/sr,'segment_end_sec':b/sr,'segment_duration_sec':(b-a)/sr,
                'segment_cut_reason':reason,
            });seg_rows.append(nr)
    real=sum(str(r.get('training_origin','real')).lower()=='real' for r in seg_rows); modeled=len(seg_rows)-real
    report={'schema':SEGMENT_SCHEMA,'segment_version':SEGMENT_VERSION,'input_rows':len(rows),'ineligible_rows_skipped':rejected,
            'segments':len(seg_rows),'real_segments':real,'modeled_segments':modeled,'min_sec':min_sec,'target_sec':target_sec,'max_sec':max_sec,
            'release_pass':bool(real>0 and modeled>0)}
    return seg_rows,report


def write_jsonl(rows: Sequence[Mapping],path:str|Path):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text('\n'.join(json.dumps(dict(x),ensure_ascii=False) for x in rows)+'\n',encoding='utf-8')
