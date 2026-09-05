from __future__ import annotations
import json, random
from pathlib import Path
import numpy as np
import soundfile as sf
import torch, torchaudio
from torch.utils.data import Dataset

class AudioManifestDataset(Dataset):
    def __init__(self, manifests, sample_rate=48000, seconds=2.0, peak_normalize=False):
        if isinstance(manifests,(str,Path)): manifests=[manifests]
        self.sr=sample_rate; self.n=int(sample_rate*seconds); self.peak_normalize=peak_normalize; self.rows=[]
        for mf in manifests:
            for line in Path(mf).read_text(encoding='utf-8').splitlines():
                if line.strip(): self.rows.append(json.loads(line))
    def __len__(self): return len(self.rows)
    def __getitem__(self,i):
        row=self.rows[i]
        audio_path=row.get('audio') or row.get('path') or row.get('file')
        if not audio_path: raise KeyError(f'Manifest row has no audio/path/file: {row}')
        audio,sr=sf.read(audio_path,dtype='float32',always_2d=True)
        wav=torch.from_numpy(np.asarray(audio).T).mean(0,keepdim=True)
        if sr!=self.sr: wav=torchaudio.functional.resample(wav,sr,self.sr)
        if wav.shape[-1] < self.n: wav=torch.nn.functional.pad(wav,(0,self.n-wav.shape[-1]))
        elif wav.shape[-1] > self.n:
            st=random.randint(0,wav.shape[-1]-self.n); wav=wav[...,st:st+self.n]
        if self.peak_normalize:
            peak=wav.abs().amax().clamp_min(1e-4); wav=wav/peak*.95
        else:
            # Preserve original dynamic relationships. Only protect against malformed >0 dBFS files.
            peak=float(wav.abs().amax())
            if peak>1.0: wav=wav/peak*.995
        return wav.clamp(-1,1), row


def audio_manifest_collate(batch):
    """Stack audio while preserving heterogeneous manifest metadata as dictionaries."""
    wavs, rows = zip(*batch)
    return torch.stack(wavs, dim=0), list(rows)
