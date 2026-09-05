"""Training-only spectral discriminators for SONICRAFT StringVAE64.

The baseline multi-resolution STFT branch follows the permissive EnCodec /
stable-audio-tools family. v1.8 adds a small log-frequency branch inspired by
the *training role* of BigVGAN-v2's pitch-aware / sub-band discriminator:
harmonic spacing and bow-noise texture are judged on a log-frequency grid.
The implementation below is independently authored in plain PyTorch and ships
with no consumer weights; stronger codec supervision therefore costs zero VST
parameters.
"""
from __future__ import annotations
import math
import torch
from torch import nn


class _ConvSpectralHead(nn.Module):
    def __init__(self, base: int = 16):
        super().__init__()
        self.net=nn.ModuleList([
            nn.Conv2d(1,base,(3,9),padding=(1,4)),
            nn.Conv2d(base,base*2,(3,9),stride=(1,2),padding=(1,4)),
            nn.Conv2d(base*2,base*4,(3,9),stride=(1,2),padding=(1,4)),
            nn.Conv2d(base*4,base*4,(3,3),padding=1),
        ])
        self.post=nn.Conv2d(base*4,1,(3,3),padding=1)

    def forward(self, h):
        feats=[]
        for layer in self.net:
            h=torch.nn.functional.leaky_relu(layer(h),.1); feats.append(h)
        return self.post(h), feats


class STFTDiscriminator(nn.Module):
    def __init__(self, n_fft: int, hop: int, base: int = 16):
        super().__init__(); self.n_fft=int(n_fft); self.hop=int(hop); self.head=_ConvSpectralHead(base)

    def forward(self, audio):
        x=audio.squeeze(1).float()
        win=torch.hann_window(self.n_fft,device=x.device,dtype=torch.float32)
        s=torch.stft(x,self.n_fft,self.hop,window=win,return_complex=True)
        h=torch.log1p(s.abs())[:,None]
        return self.head(h)


class LogFrequencySTFTDiscriminator(nn.Module):
    """Cheap pitch-aware spectral view for bowed harmonics.

    Magnitudes from an ordinary STFT are linearly interpolated at log-spaced
    frequency positions. This is not a copied CQT implementation and needs no
    extra package, while giving the critic much denser relative resolution in
    the fundamental/formant region than a linear-frequency image.
    """
    def __init__(self, n_fft: int = 2048, hop: int = 256, sample_rate: int = 48000,
                 bands: int = 112, fmin: float = 32.0, base: int = 16):
        super().__init__(); self.n_fft=int(n_fft); self.hop=int(hop); self.sample_rate=int(sample_rate)
        max_bin=self.n_fft//2
        hz=torch.logspace(math.log10(max(float(fmin),1.0)),math.log10(self.sample_rate/2.0),int(bands))
        pos=(hz/(self.sample_rate/2.0)*max_bin).clamp(0,max_bin)
        idx0=pos.floor().long(); idx1=(idx0+1).clamp(max=max_bin); frac=(pos-idx0.float()).view(1,-1,1)
        self.register_buffer('idx0',idx0,persistent=False); self.register_buffer('idx1',idx1,persistent=False)
        self.register_buffer('frac',frac,persistent=False); self.head=_ConvSpectralHead(base)

    def forward(self, audio):
        x=audio.squeeze(1).float()
        win=torch.hann_window(self.n_fft,device=x.device,dtype=torch.float32)
        s=torch.stft(x,self.n_fft,self.hop,window=win,return_complex=True).abs()
        lo=s[:,self.idx0,:]; hi=s[:,self.idx1,:]
        h=torch.log1p(lo+(hi-lo)*self.frac.to(device=s.device,dtype=s.dtype))[:,None]
        return self.head(h)


class MultiResolutionSTFTDiscriminator(nn.Module):
    def __init__(self, resolutions=((256,64),(512,128),(1024,256),(2048,512)), base=16,
                 include_log_frequency: bool = True, sample_rate: int = 48000):
        super().__init__()
        discs=[STFTDiscriminator(n,h,base) for n,h in resolutions]
        if include_log_frequency:
            discs += [LogFrequencySTFTDiscriminator(1024,128,sample_rate,96,32.0,base),
                      LogFrequencySTFTDiscriminator(2048,256,sample_rate,112,32.0,base)]
        self.discs=nn.ModuleList(discs)
    def forward(self,audio): return [d(audio) for d in self.discs]


def discriminator_hinge(real_out, fake_out):
    loss=real_out[0][0].new_tensor(0.)
    for (r,_),(f,_) in zip(real_out,fake_out):
        loss += torch.relu(1-r).mean()+torch.relu(1+f).mean()
    return loss/len(real_out)


def generator_adversarial(fake_out):
    return sum(-f.mean() for f,_ in fake_out)/len(fake_out)


def feature_matching(real_out, fake_out):
    loss=real_out[0][0].new_tensor(0.); n=0
    for (_,rf),(_,ff) in zip(real_out,fake_out):
        for r,f in zip(rf,ff): loss += (r.detach()-f).abs().mean(); n+=1
    return loss/max(1,n)
