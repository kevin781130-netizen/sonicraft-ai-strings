"""Codec/latent geometry registry shared by training and local runtime."""
from __future__ import annotations

PROFILES = {
    'dac44': {'kind':'dac44','latent_ch':1024,'latent_hz':25.0,'sample_rate':44100,'decoder_role':'dac'},
    'strings_vae64': {'kind':'strings_vae64','latent_ch':64,'latent_hz':30.0,'sample_rate':48000,'decoder_role':'string_vae64'},
}

def codec_profile(kind: str):
    k=str(kind or 'dac44').lower()
    if k in ('dac','descript_dac','dac44_16kbps'): k='dac44'
    if k not in PROFILES: raise KeyError(f'unknown codec profile: {kind}')
    return dict(PROFILES[k])
