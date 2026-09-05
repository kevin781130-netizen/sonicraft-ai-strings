import torch
from torch import nn

class ResBlock(nn.Module):
    def __init__(self,c):
        super().__init__(); self.net=nn.Sequential(nn.Conv1d(c,c,7,padding=3),nn.SiLU(),nn.Conv1d(c,c,7,padding=3))
    def forward(self,x): return torch.nn.functional.silu(x+self.net(x))

class StringCodec(nn.Module):
    """Small strings-only waveform autoencoder. Downsampling factor 256."""
    def __init__(self,latent=96):
        super().__init__()
        ch=[32,64,128,192,256]
        enc=[nn.Conv1d(1,ch[0],7,padding=3),nn.SiLU()]
        for a,b in zip(ch[:-1],ch[1:]): enc += [ResBlock(a),nn.Conv1d(a,b,8,stride=4,padding=2),nn.SiLU()]
        enc += [ResBlock(ch[-1]),nn.Conv1d(ch[-1],latent,3,padding=1)]
        self.encoder=nn.Sequential(*enc)
        dec=[nn.Conv1d(latent,ch[-1],3,padding=1),ResBlock(ch[-1])]
        for a,b in zip(ch[:0:-1],ch[-2::-1]): dec += [nn.ConvTranspose1d(a,b,8,stride=4,padding=2),nn.SiLU(),ResBlock(b)]
        dec += [nn.Conv1d(ch[0],1,7,padding=3),nn.Tanh()]
        self.decoder=nn.Sequential(*dec)
    def encode(self,x): return self.encoder(x)
    def decode(self,z): return self.decoder(z)
    def forward(self,x): return self.decode(self.encode(x))
