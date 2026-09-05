from string_ensemble_runtime_v44 import apply_ensemble_event_timing_v44

sr=48000
legacy=[{"project_sample":0,"type":1,"note":60},{"project_sample":4800,"type":2,"note":60}]
assert apply_ensemble_event_timing_v44(legacy,sr) is legacy

events=[
 {"project_sample":0,"type":4,"note":120,"velocity":.75},
 {"project_sample":0,"type":4,"note":121,"velocity":.50},
 {"project_sample":1000,"type":1,"note":60,"velocity":.8},
 {"project_sample":5000,"type":2,"note":60,"velocity":0.},
]
out=apply_ensemble_event_timing_v44(events,sr)
on=next(e for e in out if e["type"]==1)
off=next(e for e in out if e["type"]==2)
assert on["project_sample"]==1192,on
assert off["project_sample"]==4520,off
assert off["project_sample"]>on["project_sample"]
print("SONICRAFT v4.4 ensemble runtime timing smoke OK",on["project_sample"],off["project_sample"])
