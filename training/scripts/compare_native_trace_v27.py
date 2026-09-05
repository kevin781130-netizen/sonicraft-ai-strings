#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'training'))
from parity_trace_v27 import STAGES,metric,first_divergence
TOL={'raw_controls':1e-6,'frontier_context':1e-6,'initial_latent':0.0,'renderer_velocity':2e-5,'latent_after_step':2e-5,'final_latent':2e-5,'decoder_audio':3e-5,'stage_audio':5e-5,'final_mix':5e-5}
def evid(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--reference',required=True);ap.add_argument('--native',required=True);ap.add_argument('--scenario',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();r=np.load(a.reference);n=np.load(a.native)
 rows={k:metric(r[k],n[k]) for k in STAGES if k in r and k in n};fd=first_divergence(r,n,TOL);rep={'schema':2,'kind':'sonicraft_native_trace_diff_v27','scenario':a.scenario,'stages':rows,'first_divergence':fd,'passed':fd is None};rep['evidence_id']=evid(rep);Path(a.out).write_text(json.dumps(rep,indent=2),encoding='utf-8');print('PARITY TRACE',a.scenario,'PASS' if rep['passed'] else 'FAIL',fd);raise SystemExit(0 if rep['passed'] else 3)
if __name__=='__main__':main()
