"""No-onnxruntime wiring smoke: fake sessions verify NumPy controls/sampler/decoder/stage."""
from __future__ import annotations
import sys,types,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ort_model_backend import ORTFlowBackend
from protocol import RequestHeader,TYPE_RENDER
class RenderSession:
    def run(self,_,feed):return [np.zeros_like(feed['latent'],dtype=np.float32)+.01]
class DecodeSession:
    def run(self,_,feed):
        z=feed['latent'];return [np.repeat(np.mean(z,axis=1,keepdims=True),1600,axis=2).astype(np.float32)]

def main():
    b=ORTFlowBackend(Path('/tmp/no-models'),steps=2,auto_steps=1);b.renderer=RenderSession();b.decoder=DecodeSession();b.backend_name='ort-fake';b.provider='fake';b.meta={'latent_ch':64,'latent_hz':30.,'codec_sample_rate':48000,'sampling_family':'shortcut','supported_steps':[1,2,4,8],'recommended_steps':1};b.fingerprint=lambda:'fake-v22'
    sr=48000;req=RequestHeader(TYPE_RENDER,1,0,sr//4,sr,2,4,1,68.,.35,1<<25);ctrl=[.7,.5,.9,.85,.5,1.,1.,.18,.5,0.,.5,.5,.4,0.]
    ev=[{'project_sample':0,'type':1,'part':0,'note':69,'articulation':0,'velocity':.8,'tempo_bpm':68.,'controls':ctrl},{'project_sample':sr//8,'type':2,'part':0,'note':69,'articulation':0,'velocity':0.,'tempo_bpm':68.,'controls':ctrl}]
    x=b.render(req,ev);assert x.shape==(sr//4,34) and np.isfinite(x).all() and np.max(np.abs(x))>0
    print('v2.2 ORT NO-TORCH WIRING PASS',x.shape,float(np.max(np.abs(x))))
if __name__=='__main__':main()
