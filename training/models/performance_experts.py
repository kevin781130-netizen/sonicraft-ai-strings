from __future__ import annotations
import torch
from torch import nn

class _Context(nn.Module):
    """Compact shared musical context encoder for the physical performance heads.

    These heads never change MIDI note identity. They predict *how* a requested transition
    should be executed from tempo, interval, register, dynamics and phrase context.
    """
    def __init__(self, hidden=128, instruments=3):
        super().__init__(); self.instrument=nn.Embedding(instruments,16)
        self.net=nn.Sequential(nn.Linear(13+16,hidden),nn.SiLU(),nn.LayerNorm(hidden),nn.Linear(hidden,hidden),nn.SiLU())
    def forward(self,pitch,dynamics,note_progress,phrase_position,prev_interval,next_interval,
                tempo_bpm,note_duration_beats,speed_quantile,transition_speed,attack_character,
                legato,velocity,instrument):
        x=torch.stack([pitch/127.0,dynamics,note_progress,phrase_position,
                       prev_interval/24.0,next_interval/24.0,tempo_bpm/200.0,
                       note_duration_beats/8.0,speed_quantile,transition_speed,
                       attack_character,legato,velocity],-1)
        emb=self.instrument(instrument.long())
        if emb.ndim==2 and x.ndim==3: emb=emb[:,None,:].expand(-1,x.shape[1],-1)
        return self.net(torch.cat([x,emb],-1))

class PerformanceExperts(nn.Module):
    """Separate Legato, Portamento and Bow-change experts.

    Normalized outputs:
      legato:    transition_beats/.40, overlap_ratio, attack_suppression, continuity
      portamento:transition_beats/.80, slide_extent_ratio, curve_shape_norm, arrival_softness
      bow:       transition_beats/.25, transient_strength, brightness_delta[-1,1], continuity
    """
    def __init__(self,hidden=128,instruments=3):
        super().__init__();self.ctx=_Context(hidden,instruments)
        self.legato=nn.Linear(hidden,4);self.portamento=nn.Linear(hidden,4);self.bow=nn.Linear(hidden,4)
    @staticmethod
    def _sigmoid4(y): return torch.sigmoid(y)
    def forward(self,*args):
        h=self.ctx(*args)
        l=self._sigmoid4(self.legato(h))
        p=self._sigmoid4(self.portamento(h))
        braw=self.bow(h); b=torch.cat([torch.sigmoid(braw[...,:2]),torch.tanh(braw[...,2:3]),torch.sigmoid(braw[...,3:4])],-1)
        return {'legato':l,'portamento':p,'bow':b}
