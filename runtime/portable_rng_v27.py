"""SONICRAFT v2.7 portable deterministic RNG contract.

The contract is intentionally tiny and backend-independent so Python/NumPy/Torch/C++
can start from identical latent noise and Retake residuals.
"""
from __future__ import annotations
import math
import numpy as np

MASK=(1<<64)-1

def fnv1a64(text:str)->int:
    h=1469598103934665603
    for b in text.encode('utf-8'):
        h ^= b; h = (h*1099511628211)&MASK
    return h

def splitmix64(x:int)->int:
    x=(x+0x9E3779B97F4A7C15)&MASK
    z=x
    z=((z^(z>>30))*0xBF58476D1CE4E5B9)&MASK
    z=((z^(z>>27))*0x94D049BB133111EB)&MASK
    return (z^(z>>31))&MASK

def uniform01(state:int):
    state=splitmix64(state)
    # Match C++ exactly: use top 53 bits as a double in (0,1).
    u=((state>>11)+0.5)/(1<<53)
    return state,float(u)

def normal_array(key:str,n:int)->np.ndarray:
    state=fnv1a64(key); out=np.empty(int(n),np.float32); i=0
    while i<n:
        state,u1=uniform01(state); state,u2=uniform01(state)
        u1=max(u1,1e-15)
        r=math.sqrt(-2.0*math.log(u1)); th=2.0*math.pi*u2
        out[i]=np.float32(r*math.cos(th)); i+=1
        if i<n: out[i]=np.float32(r*math.sin(th)); i+=1
    return out

def event_seed_key(start_sample:int,end_sample:int,sample_rate:int,part:int,voice:int,events)->str:
    chunks=[f'v27|s={int(start_sample)}|e={int(end_sample)}|sr={int(sample_rate)}|p={int(part)}|v={int(voice)}']
    for e in events:
        if isinstance(e,dict):
            vals=(int(e.get('project_sample',0)),int(e.get('type',0)),int(e.get('part',0)),int(e.get('note',0)),int(e.get('articulation',0)),int(round(float(e.get('velocity',0))*1_000_000)))
        else:
            vals=(int(e.sample),int(e.type),int(e.part),int(e.note),int(e.articulation),int(round(float(e.velocity)*1_000_000)))
        chunks.append(','.join(map(str,vals)))
    return '|'.join(chunks)
