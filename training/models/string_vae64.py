"""48 kHz / 64-d continuous strings VAE challenger.

Geometry intentionally follows the strongest useful MIT public baseline found in the
v1.6 scout (SoundReactor/Oobleck family): 48 kHz waveform, 1600x temporal reduction,
64 continuous latent channels. SONICRAFT keeps only the geometry/block ideas and trains
its own rights-cleared strings weights. The default network is narrowed for a much
smaller decoder; upstream weights are never required or bundled.
"""
from __future__ import annotations
import math
import torch
from torch import nn
import torch.nn.functional as F


DEFAULT_STRIDES = (2, 4, 5, 5, 8)
DEFAULT_MULTS = (1, 2, 4, 8, 16)


class SnakeBeta(nn.Module):
    """Small learnable periodic activation; pure PyTorch, no alias-free runtime dep."""
    def __init__(self, channels: int):
        super().__init__()
        self.log_alpha = nn.Parameter(torch.zeros(1, channels, 1))
        self.log_beta = nn.Parameter(torch.zeros(1, channels, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        alpha = F.softplus(self.log_alpha) + 1e-4
        beta = F.softplus(self.log_beta) + 1e-4
        return x + torch.sin(alpha * x).square() / beta


class ResidualUnit(nn.Module):
    def __init__(self, channels: int, dilation: int):
        super().__init__()
        pad = dilation * 3
        self.a1 = SnakeBeta(channels)
        self.c1 = nn.Conv1d(channels, channels, 7, dilation=dilation, padding=pad)
        self.a2 = SnakeBeta(channels)
        self.c2 = nn.Conv1d(channels, channels, 1)

    def forward(self, x):
        return x + self.c2(self.a2(self.c1(self.a1(x))))


class EncoderBlock(nn.Module):
    def __init__(self, cin: int, cout: int, stride: int):
        super().__init__()
        p = int(math.ceil(stride / 2))
        self.res = nn.Sequential(*(ResidualUnit(cin, d) for d in (1, 3, 9)))
        self.act = SnakeBeta(cin)
        self.down = nn.Conv1d(cin, cout, kernel_size=2 * stride, stride=stride, padding=p)

    def forward(self, x):
        return self.down(self.act(self.res(x)))


class DecoderBlock(nn.Module):
    def __init__(self, cin: int, cout: int, stride: int):
        super().__init__()
        p = int(math.ceil(stride / 2))
        op = 1 if stride % 2 else 0
        self.act = SnakeBeta(cin)
        self.up = nn.ConvTranspose1d(cin, cout, kernel_size=2 * stride, stride=stride,
                                     padding=p, output_padding=op)
        self.res = nn.Sequential(*(ResidualUnit(cout, d) for d in (1, 3, 9)))

    def forward(self, x):
        return self.res(self.up(self.act(x)))


class StringVAE64Encoder(nn.Module):
    def __init__(self, channels: int = 16, latent_dim: int = 64,
                 c_mults=DEFAULT_MULTS, strides=DEFAULT_STRIDES):
        super().__init__()
        if len(c_mults) != len(strides):
            raise ValueError('c_mults and strides must have equal length')
        widths = [int(channels)] + [int(channels * m) for m in c_mults]
        layers = [nn.Conv1d(1, widths[0], 7, padding=3)]
        for i, stride in enumerate(strides):
            layers.append(EncoderBlock(widths[i], widths[i + 1], int(stride)))
        layers += [SnakeBeta(widths[-1]), nn.Conv1d(widths[-1], 2 * latent_dim, 3, padding=1)]
        self.layers = nn.Sequential(*layers)

    def forward(self, audio):
        h = self.layers(audio)
        return h.chunk(2, 1)


class StringVAE64Decoder(nn.Module):
    def __init__(self, channels: int = 16, latent_dim: int = 64,
                 c_mults=DEFAULT_MULTS, strides=DEFAULT_STRIDES, final_tanh: bool = False):
        super().__init__()
        if len(c_mults) != len(strides):
            raise ValueError('c_mults and strides must have equal length')
        widths = [int(channels)] + [int(channels * m) for m in c_mults]
        layers = [nn.Conv1d(latent_dim, widths[-1], 7, padding=3)]
        current = widths[-1]
        for i in range(len(strides) - 1, -1, -1):
            cout = widths[i]
            layers.append(DecoderBlock(current, cout, int(strides[i])))
            current = cout
        layers += [SnakeBeta(widths[0]), nn.Conv1d(widths[0], 1, 7, padding=3),
                   nn.Tanh() if final_tanh else nn.Identity()]
        self.layers = nn.Sequential(*layers)

    def forward(self, z):
        return self.layers(z)

    def decode(self, z):
        return self.forward(z)


class StringVAE64(nn.Module):
    sample_rate = 48000
    latent_dim = 64
    downsampling_ratio = 1600
    latent_hz = 30.0
    codec_kind = 'strings_vae64'

    def __init__(self, channels: int = 16, latent_dim: int = 64,
                 c_mults=DEFAULT_MULTS, strides=DEFAULT_STRIDES, final_tanh: bool = False):
        super().__init__()
        self.channels = int(channels); self.latent_dim = int(latent_dim)
        self.c_mults = tuple(int(x) for x in c_mults); self.strides = tuple(int(x) for x in strides)
        self.downsampling_ratio = math.prod(self.strides)
        self.latent_hz = self.sample_rate / self.downsampling_ratio
        self.encoder = StringVAE64Encoder(self.channels, self.latent_dim, self.c_mults, self.strides)
        self.decoder = StringVAE64Decoder(self.channels, self.latent_dim, self.c_mults, self.strides, final_tanh)

    def encode_stats(self, x):
        return self.encoder(x)

    def encode(self, x, sample: bool = False):
        mu, logvar = self.encode_stats(x)
        if not sample:
            return mu
        eps = torch.randn_like(mu)
        return mu + torch.exp(0.5 * logvar.clamp(-20, 10)) * eps

    def decode(self, z):
        return self.decoder(z)

    def forward(self, x, sample: bool = True):
        mu, logvar = self.encode_stats(x)
        z = mu if not sample else mu + torch.exp(0.5 * logvar.clamp(-20, 10)) * torch.randn_like(mu)
        return self.decode(z), mu, logvar

    def config(self):
        return {'channels': self.channels, 'latent_dim': self.latent_dim,
                'c_mults': list(self.c_mults), 'strides': list(self.strides), 'final_tanh': False}
