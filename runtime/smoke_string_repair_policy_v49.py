from pathlib import Path
import tempfile
from string_repair_policy_v49 import RepairPolicyMemoryV49
with tempfile.TemporaryDirectory() as td:
    p=Path(td)/"policy.json";m=RepairPolicyMemoryV49(p)
    s0=m.snapshot()
    assert s0.generation==0 and all(abs(v-1)<1e-9 for v in s0.values.values())
    r=m.learn("B",.01,.9,.9);assert not r["learned"] and r["reason"]=="low_margin"
    r=m.learn("B",.10,.2,.9);assert not r["learned"] and r["reason"]=="safety_floor"
    r=m.learn("B",.10,.9,.9);assert r["learned"]
    s1=m.snapshot();assert s1.generation==1 and s1.values["smoothing"]>1 and s1.values["transition"]>1
    # Reload proves persistence/hash determinism.
    m2=RepairPolicyMemoryV49(p);s2=m2.snapshot()
    assert s2.generation==s1.generation and s2.profile_hash==s1.profile_hash
    assert s2.values==s1.values
print("SONICRAFT v4.9 repair policy memory/gates smoke OK")
