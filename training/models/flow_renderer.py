import math, torch
from torch import nn

class FlowRenderer(nn.Module):
    def __init__(self,latent_ch=96,d_model=256,layers=6,heads=8,articulations=8):
        super().__init__(); self.latent_ch=latent_ch; self.d_model=d_model
        self.xproj=nn.Linear(latent_ch,d_model)
        self.pitch=nn.Linear(2,d_model) # pitch/127 + gate
        self.dyn=nn.Linear(1,d_model)
        self.instrument=nn.Embedding(3,d_model)
        self.art=nn.Embedding(articulations,d_model)
        self.time=nn.Sequential(nn.Linear(2,d_model),nn.SiLU(),nn.Linear(d_model,d_model))
        layer=nn.TransformerEncoderLayer(d_model,heads,d_model*4,batch_first=True,norm_first=True,activation='gelu')
        self.net=nn.TransformerEncoder(layer,layers)
        self.out=nn.Linear(d_model,latent_ch)
    def forward(self,xt,t,pitch,gate,dynamics,instrument,articulation=None):
        # xt [B,C,T], conditions [B,Tc]; interpolate conditions to latent rate.
        B,C,T=xt.shape
        def interp(v): return torch.nn.functional.interpolate(v[:,None].float(),size=T,mode='linear',align_corners=False)[:,0]
        p=interp(pitch)/127.; g=interp(gate); d=interp(dynamics)
        h=self.xproj(xt.transpose(1,2))+self.pitch(torch.stack([p,g],-1))+self.dyn(d[...,None])+self.instrument(instrument)[:,None,:]
        if articulation is None: articulation=torch.zeros(B,dtype=torch.long,device=xt.device)
        h=h+self.art(articulation)[:,None,:]
        te=torch.stack([torch.sin(t*math.pi),torch.cos(t*math.pi)],-1); h=h+self.time(te)[:,None,:]
        return self.out(self.net(h)).transpose(1,2)
