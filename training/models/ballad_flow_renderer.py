import math
import torch
from torch import nn
import torch.nn.functional as F
from models.vibrato_expert import VibratoControlExpert
from models.performance_experts import PerformanceExperts
from models.adaptive_flow_dit import AdaptiveFlowDiT


class LowRankContextAdapter(nn.Module):
    """Tiny zero-start adapter for hidden quartet/phrase context.

    The final projection is zero-initialized, so enabling the module is behavior-neutral
    until a quartet fine-tune teaches it useful residuals. Written MIDI/CC never enters
    this adapter as an editable target; it can only influence the renderer condition.
    """
    def __init__(self, in_dim: int, out_dim: int, rank: int = 24):
        super().__init__()
        self.in_dim=int(in_dim); self.rank=int(rank)
        self.norm=nn.LayerNorm(self.in_dim, elementwise_affine=False, eps=1e-6)
        self.down=nn.Linear(self.in_dim,self.rank)
        self.up=nn.Linear(self.rank,int(out_dim))
        nn.init.zeros_(self.up.weight); nn.init.zeros_(self.up.bias)

    def forward(self, x):
        return self.up(F.silu(self.down(self.norm(x))))


class BalladFlowRenderer(nn.Module):
    """Strings-only rectified-flow renderer with tempo-aware performance experts.

    User MIDI remains authoritative. The model receives familiar CC1/CC3/CC11 plus hidden
    phrase/timing features. v0.8 keeps beat-normalized learned timing, separate Legato/Portamento/Bow experts and project-tempo context
    without adding mandatory DAW automation lanes.
    """
    CONTROL_DIMS = 34  # 26 raw controls + transition-beats + speed-quantile + 6 validity flags

    def __init__(self, latent_ch=1024, d_model=384, layers=8, heads=8,
                 articulations=12, players=4, instruments=3, dropout=.05,
                 backbone='transformer', mlp_ratio=3.0, attention_impl='mha',
                 shared_adaln=False, weight_tied=False, interval_conditioning=False,
                 expert_fusion='separate', split_vibrato_validity=False,
                 frontier_context_dim=0, context_rank=24):
        super().__init__()
        self.latent_ch = latent_ch
        self.d_model = d_model
        self.articulations = articulations
        self.backbone = str(backbone).lower()
        self.mlp_ratio = float(mlp_ratio)
        self.attention_impl = str(attention_impl).lower()
        self.shared_adaln = bool(shared_adaln)
        self.weight_tied = bool(weight_tied)
        self.interval_conditioning = bool(interval_conditioning)
        self.expert_fusion_kind = str(expert_fusion).lower()
        self.split_vibrato_validity = bool(split_vibrato_validity)
        self.frontier_context_dim = int(frontier_context_dim)
        self.context_rank = int(context_rank)
        self.xproj = nn.Linear(latent_ch, d_model)
        self.ctrl = nn.Sequential(
            nn.Linear(self.CONTROL_DIMS, d_model), nn.SiLU(), nn.Linear(d_model, d_model)
        )
        self.instrument = nn.Embedding(instruments, d_model)
        self.art = nn.Embedding(articulations, d_model)
        self.player = nn.Embedding(players, d_model)
        self.frontier_context = (LowRankContextAdapter(self.frontier_context_dim,d_model,self.context_rank)
                                 if self.frontier_context_dim>0 else None)
        # Keep the legacy Fourier-lite time MLP only for legacy Transformer checkpoints.
        self.time = nn.Sequential(nn.Linear(4, d_model), nn.SiLU(), nn.Linear(d_model, d_model)) if self.backbone == 'transformer' else None

        # v0.8 physical experts are the SAME modules that can be supervised/pretrained
        # independently. This closes the old gap where an expert checkpoint existed but
        # the HQ renderer had a separate unrelated residual MLP.
        self.vibrato_physics = VibratoControlExpert(hidden=128, instruments=instruments)
        self.performance_experts = PerformanceExperts(hidden=128, instruments=instruments)
        if self.expert_fusion_kind == 'separate':
            # Exact legacy path for v1.4-v1.6 checkpoints.
            self.vibrato_proj = nn.Sequential(nn.Linear(4, d_model), nn.SiLU(), nn.Linear(d_model, d_model))
            self.legato_proj = nn.Sequential(nn.Linear(4, d_model), nn.SiLU(), nn.Linear(d_model, d_model))
            self.portamento_proj = nn.Sequential(nn.Linear(4, d_model), nn.SiLU(), nn.Linear(d_model, d_model))
            self.bow_proj = nn.Sequential(nn.Linear(4, d_model), nn.SiLU(), nn.Linear(d_model, d_model))
            self.expert_fusion = None
        elif self.expert_fusion_kind == 'joint':
            # Frontier compression: four gated 4-D expert states are fused once. This is
            # smaller than four independent d_model-wide MLPs and can learn cross-expert
            # interactions (e.g. bow/legato/vibrato coupling) inside one projection.
            self.vibrato_proj = self.legato_proj = self.portamento_proj = self.bow_proj = None
            self.expert_fusion = nn.Sequential(nn.Linear(16, d_model), nn.SiLU(), nn.Linear(d_model, d_model))
        else:
            raise ValueError(f'unknown expert fusion: {expert_fusion}')

        if self.backbone == 'transformer':
            # Exact legacy topology for backward compatibility with v1.4 checkpoints.
            layer = nn.TransformerEncoderLayer(
                d_model, heads, d_model * 4, batch_first=True, norm_first=True,
                activation='gelu', dropout=dropout
            )
            self.net = nn.TransformerEncoder(layer, layers)
        elif self.backbone in ('adaln_dit', 'dit'):
            self.net = AdaptiveFlowDiT(
                dim=d_model, depth=layers, heads=heads, mlp_ratio=self.mlp_ratio, dropout=dropout,
                attention_impl=self.attention_impl, shared_adaln=self.shared_adaln,
                weight_tied=self.weight_tied, interval_conditioning=self.interval_conditioning
            )
        else:
            raise ValueError(f'unknown renderer backbone: {backbone}')
        self.out_norm = nn.LayerNorm(d_model)
        self.out = nn.Linear(d_model, latent_ch)

    @staticmethod
    def _interp(v, T):
        if v.ndim == 1:
            v = v[:, None]
        return F.interpolate(v[:, None].float(), size=T, mode='linear', align_corners=False)[:, 0]

    @staticmethod
    def _interp_ids(v, T):
        if v.ndim == 1:
            v = v[:, None]
        return F.interpolate(v[:, None].float(), size=T, mode='nearest')[:, 0].long()

    def forward(self, xt, t, pitch, gate, onset, velocity, dynamics, vibrato, expression,
                legato, pitchbend, transition_speed, short_tightness, attack_character,
                note_progress, phrase_position, prev_interval, next_interval,
                bow_change_prob, vibrato_onset, tempo_bpm, seconds_per_beat,
                note_duration_beats, transition_target_ms, speed_profile,
                vibrato_depth_cents, vibrato_rate_hz, vibrato_jitter,
                dynamics_known, vibrato_known, expression_known, legato_known,
                pitchbend_known, timing_known, articulation_known,
                instrument, articulation, player, articulation_curve=None, flow_h=None,
                vibrato_physics_known=None, frontier_context=None):
        B, C, T = xt.shape
        vals = [pitch, gate, onset, velocity, dynamics, vibrato, expression, legato, pitchbend,
                transition_speed, short_tightness, attack_character, note_progress,
                phrase_position, prev_interval, next_interval, bow_change_prob, vibrato_onset,
                tempo_bpm, seconds_per_beat, note_duration_beats, transition_target_ms,
                speed_profile, vibrato_depth_cents, vibrato_rate_hz, vibrato_jitter]
        masks = [dynamics_known, vibrato_known, expression_known, legato_known,
                 pitchbend_known, timing_known, articulation_known]
        vals = [self._interp(v, T) for v in vals]
        masks = [self._interp(v, T) for v in masks]
        # v1.7 separates two concepts that v1.6 overloaded into one flag:
        # - vibrato_known: user/score CC3 availability (authoritative at runtime),
        # - vibrato_physics_known: measured depth/rate/onset/jitter labels for teacher forcing.
        # Legacy checkpoints keep the old behavior by default.
        if self.split_vibrato_validity:
            physics_vib_known = self._interp(vibrato_known if vibrato_physics_known is None else vibrato_physics_known, T)
        else:
            physics_vib_known = masks[1]
        # Beat-domain transition timing is the invariant learned from performance data.
        # Milliseconds are then a consequence of the current Cubase tempo.
        raw_spb = vals[19].clamp_min(0.10)
        raw_transition_ms = vals[21].clamp_min(0.0)
        transition_beats = (raw_transition_ms / 1000.0) / raw_spb
        sp = vals[22]
        speed_quantile = torch.where(sp < .17, torch.full_like(sp,.50),
                         torch.where(sp < .50, torch.full_like(sp,.80),
                         torch.where(sp < .84, torch.full_like(sp,.50), torch.full_like(sp,.20))))
        vals[0] = vals[0] / 127.0
        vals[18] = vals[18] / 200.0        # BPM
        vals[19] = vals[19] / 1.5          # seconds/beat
        vals[20] = vals[20] / 8.0          # duration in beats
        vals[21] = vals[21] / 500.0        # transition ms
        vals[23] = vals[23] / 100.0        # vibrato peak cents
        vals[24] = vals[24] / 10.0         # vibrato Hz

        # Unknown controls are neutralized but accompanied by explicit validity flags.
        for idx, mask in zip(range(4, 9), masks[:5]):
            vals[idx] = vals[idx] * mask
        for idx in range(18, 23):
            vals[idx] = vals[idx] * masks[5]
        for idx in range(23, 26):
            vals[idx] = vals[idx] * physics_vib_known

        # 26 performance values + learned/inferred beat-domain timing + 6 continuous validity flags.
        controls = torch.stack(vals + [transition_beats, speed_quantile] + masks[:6], -1)
        cond = self.ctrl(controls)
        cond = cond + self.instrument(instrument)[:, None, :] + self.player(player)[:, None, :]
        if self.frontier_context is not None:
            if frontier_context is None:
                fc=torch.zeros(B,T,self.frontier_context_dim,device=xt.device,dtype=xt.dtype)
            else:
                fc=frontier_context
                if fc.ndim==2: fc=fc[:,None,:]
                # Runtime convention is [B, C, frames]; training tools may provide [B, frames, C].
                if fc.ndim!=3: raise ValueError('frontier_context must be rank-3')
                if fc.shape[-1]==self.frontier_context_dim:
                    pass
                elif fc.shape[1]==self.frontier_context_dim:
                    fc=fc.transpose(1,2)
                else:
                    raise ValueError(f'frontier_context dimension mismatch: expected {self.frontier_context_dim}')
                if fc.shape[1]!=T:
                    fc=F.interpolate(fc.transpose(1,2).float(),size=T,mode='linear',align_corners=False).transpose(1,2)
                fc=fc.to(device=xt.device,dtype=cond.dtype)
            cond = cond + self.frontier_context(fc)

        if articulation_curve is None:
            art_ids = articulation[:, None].expand(B, T)
        else:
            art_ids = self._interp_ids(articulation_curve, T).clamp_(0, self.articulations - 1)
        art_known = masks[-1]
        cond = cond + self.art(art_ids) * art_known[..., None]

        # Physical experts: CC3 drives requested depth; tempo changes transition timing but
        # never phase-locks vibrato to the metronome. The standalone supervised expert
        # checkpoints can be loaded directly into these exact submodules before HQ training.
        raw_pitch = vals[0] * 127.0
        raw_bpm = vals[18] * 200.0
        raw_durb = vals[20] * 8.0
        raw_vib_depth = vals[23] * 100.0
        raw_vib_rate = vals[24] * 10.0
        # Use the learned expert prediction as the runtime-capable path. During training the
        # measured physical controls are still present in the base condition when known.
        vib_phys = self.vibrato_physics(
            vals[5], vals[4], raw_pitch, vals[12], vals[13], raw_bpm, raw_durb, vals[22], instrument
        )
        perf = self.performance_experts(
            raw_pitch, vals[4], vals[12], vals[13], vals[14], vals[15],
            raw_bpm, raw_durb, speed_quantile, vals[9], vals[11], vals[7], vals[3], instrument
        )
        # When true physical labels exist, softly teacher-force their measured vibrato state
        # into the residual representation while retaining the expert prediction for runtime.
        measured_vib = torch.stack([raw_vib_depth/100.0, raw_vib_rate/10.0, vals[17], vals[25]], -1)
        vk = physics_vib_known[...,None]
        vib_condition = vib_phys * (1.0 - .35*vk) + measured_vib * (.35*vk)
        # v1.7 strict authority: availability is not expression strength. For new split-validity
        # checkpoints, the user's normalized CC3 value drives vibrato residual strength; the
        # validity bit only decides whether the authored lane is known. Legacy checkpoints keep
        # their exact historical gate to preserve strict state/behavior compatibility.
        vib_gate=((.15 + .85*vals[5]) if self.split_vibrato_validity else (.15 + .85*torch.maximum(vals[5], masks[1])))[..., None]
        legato_gate=(.10 + .90*torch.maximum(vals[7], (art_ids==1).float()))[...,None]
        portamento_gate=(.04 + .96*(art_ids==2).float())[...,None]
        bow_gate=(.12 + .88*vals[16])[...,None]
        if self.expert_fusion_kind == 'joint':
            expert_state=torch.cat([
                vib_condition*vib_gate,
                perf['legato']*legato_gate,
                perf['portamento']*portamento_gate,
                perf['bow']*bow_gate,
            ],-1)
            cond = cond + self.expert_fusion(expert_state)
        else:
            cond = cond + self.vibrato_proj(vib_condition) * vib_gate
            cond = cond + self.legato_proj(perf['legato']) * legato_gate
            cond = cond + self.portamento_proj(perf['portamento']) * portamento_gate
            cond = cond + self.bow_proj(perf['bow']) * bow_gate

        h = self.xproj(xt.transpose(1, 2)) + cond

        if self.backbone == 'transformer':
            te = torch.stack([
                torch.sin(t * math.pi), torch.cos(t * math.pi),
                torch.sin(t * 2 * math.pi), torch.cos(t * 2 * math.pi)
            ], -1)
            h = h + self.time(te)[:, None, :]
            h = self.net(h)
        else:
            # Note-active weighted pooling prevents long silent tails from dominating
            # the global AdaLN condition while preserving every frame-local control in h.
            w = (.15 + .85 * vals[1].clamp(0, 1))[..., None]
            phrase_condition = (cond * w).sum(1) / w.sum(1).clamp_min(1e-4)
            h = self.net(h, t, phrase_condition, flow_h=flow_h)
        return self.out(self.out_norm(h)).transpose(1, 2)
