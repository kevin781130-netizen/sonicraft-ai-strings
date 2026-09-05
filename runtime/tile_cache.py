"""Small persistent mono tile cache for incremental DAW shadow rendering."""
from __future__ import annotations
import os, time
from pathlib import Path
import numpy as np


class AudioTileCache:
    def __init__(self, root, max_mb=768.0):
        self.root=Path(root) if root else None
        self.max_bytes=max(64*1024*1024,int(float(max_mb)*1024*1024))
        self.last_prune=0.0
        if self.root: self.root.mkdir(parents=True,exist_ok=True)

    def _path(self,key): return self.root/(str(key)+'.f32') if self.root else None

    def get(self,key,frames):
        p=self._path(key)
        if p is None or not p.is_file(): return None
        try:
            raw=p.read_bytes(); frames=int(frames)
            if len(raw)!=frames*4: return None
            os.utime(p,None)
            return np.frombuffer(raw,dtype='<f4').copy()
        except OSError:
            return None

    def put(self,key,audio):
        p=self._path(key)
        if p is None: return
        try:
            a=np.asarray(audio,dtype='<f4').reshape(-1)
            tmp=p.with_suffix('.tmp'); tmp.write_bytes(a.tobytes()); os.replace(tmp,p)
            self.prune()
        except OSError:
            pass

    def prune(self,force=False):
        if not self.root: return
        now=time.time()
        if not force and now-self.last_prune<60: return
        self.last_prune=now
        try:
            files=[p for p in self.root.glob('*.f32') if p.is_file()]
            total=sum(p.stat().st_size for p in files)
            if total<=self.max_bytes: return
            target=int(self.max_bytes*.85)
            for p in sorted(files,key=lambda x:x.stat().st_mtime):
                if total<=target: break
                try:
                    size=p.stat().st_size; p.unlink(missing_ok=True); total-=size
                except OSError: pass
        except OSError:
            pass
