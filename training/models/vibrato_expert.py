import torch
from torch import nn

class VibratoControlExpert(nn.Module):
    """Maps the familiar CC3 lane + musical context to physical vibrato behavior.

    Outputs (normalized): depth_cents/100, rate_hz/10, onset_ms/1000, micro-jitter.
    The main renderer can consume these physical controls while the user still edits only CC3.
    """
    def __init__(self, hidden=128, instruments=3):
        super().__init__()
        self.instrument=nn.Embedding(instruments,16)
        self.net=nn.Sequential(
            nn.Linear(9+16,hidden),nn.SiLU(),nn.LayerNorm(hidden),
            nn.Linear(hidden,hidden),nn.SiLU(),nn.Linear(hidden,4)
        )
    def forward(self, cc3, dynamics, pitch, note_progress, phrase_position,
                tempo_bpm, note_duration_beats, speed_profile, instrument):
        vals=[cc3,dynamics,pitch/127.0,note_progress,phrase_position,
              tempo_bpm/200.0,note_duration_beats/8.0,speed_profile,
              torch.ones_like(cc3)]
        x=torch.stack(vals,-1)
        emb=self.instrument(instrument.long())
        if emb.ndim==2 and x.ndim==3: emb=emb[:,None,:].expand(-1,x.shape[1],-1)
        y=self.net(torch.cat([x,emb],-1))
        depth=torch.sigmoid(y[...,0])*.90
        rate=.35 + torch.sigmoid(y[...,1])*.45   # 3.5-8.0 Hz represented /10
        onset=torch.sigmoid(y[...,2])*.65        # 0-650 ms represented /1000
        jitter=torch.sigmoid(y[...,3])*.10
        return torch.stack([depth,rate,onset,jitter],-1)
