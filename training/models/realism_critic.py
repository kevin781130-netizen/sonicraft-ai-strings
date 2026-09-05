import torch
from torch import nn

class RealismCritic(nn.Module):
    """Small reference discriminator for ensemble texture/room balance.
    It is a training/evaluation aid only; it never receives MIDI authority.
    """
    def __init__(self, n_fft=1024, hidden=64):
        super().__init__(); self.n_fft=n_fft
        self.net=nn.Sequential(
            nn.Conv2d(1,hidden,5,2,2),nn.LeakyReLU(.2),
            nn.Conv2d(hidden,hidden*2,3,2,1),nn.LeakyReLU(.2),
            nn.Conv2d(hidden*2,hidden*4,3,2,1),nn.LeakyReLU(.2),
            nn.AdaptiveAvgPool2d((1,1)),nn.Flatten(),nn.Linear(hidden*4,1))
    def features(self,wav):
        if wav.dim()==2: wav=wav[:,None,:]
        win=torch.hann_window(self.n_fft,device=wav.device)
        x=wav.mean(1)
        s=torch.stft(x,self.n_fft,self.n_fft//4,window=win,return_complex=True).abs().clamp_min(1e-5).log()
        return s[:,None]
    def forward(self,wav): return self.net(self.features(wav))
