from __future__ import annotations
from pathlib import Path
import tempfile, numpy as np
from judge_memory_v38 import JudgeMemory
with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'profile.json';m=JudgeMemory(p)
    scores=np.array([[.82,.80,.78,.76,.79,.90],[.84,.88,.70,.72,.80,.92],[.81,.70,.90,.75,.82,.91],[.80,.73,.72,.92,.76,.93]],np.float32)
    s0=m.snapshot();assert s0.confidence==0 and s0.evidence==0
    s1=m.learn('commit',1,scores);assert abs(s1.evidence-1.35)<1e-6 and 0.09<s1.confidence<0.11
    assert s1.weights[4]>=0
    # persistence across service/model restart
    m2=JudgeMemory(p);s2=m2.snapshot();assert abs(s2.evidence-1.35)<1e-6 and np.allclose(s1.weights,s2.weights)
    # bounded taste layer cannot move score by > .12 and unsafe take cannot receive positive bonus.
    bad=scores.copy();bad[3,5]=.1
    w,personal,s=m2.personalize(bad,True,1.0)
    assert np.max(np.abs(personal-bad[:,0]))<=.120001
    assert personal[3]<=bad[3,0]+1e-7
    m2.clear();assert m2.snapshot().evidence==0 and not p.exists()
print('SONICRAFT v3.8 Judge Memory smoke OK evidence=1.35 confidence=',round(s1.confidence,4))
