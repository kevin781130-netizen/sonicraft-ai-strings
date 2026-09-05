#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def evok(d):
    if not isinstance(d,dict) or not d.get('evidence_id'):return False
    x=dict(d);eid=x.pop('evidence_id');return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()==eid
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--product-promotion',required=True);ap.add_argument('--latency-benchmark',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();p=load(a.product_promotion);b=load(a.latency_benchmark);r=[]
    if not p.get('promotion_pass') or len(str(p.get('product_promotion_id','')))!=64:r.append('v24_product_not_promoted')
    if not evok(b) or not b.get('passed'):r.append('v25_latency_benchmark_failed')
    if b.get('audio_engine')!='WASAPI_EVENT_SHARED_IAUDIOCLIENT3':r.append('wasapi_event_engine_required')
    if b.get('midi_timestamp_source')!='WinMM_dwParam2_driver_timestamp':r.append('driver_timestamped_midi_required')
    if 40 not in [int(x) for x in b.get('adaptive_quantum_ms',[])]:r.append('40ms_attack_quantum_required')
    base={'schema':1,'kind':'sonicraft_ultra_low_latency_promotion_v25','product_promotion_id':p.get('product_promotion_id'),'latency_evidence_id':b.get('evidence_id'),'audio_engine':b.get('audio_engine'),'attack_p95_service_ms':b.get('attack_p95_service_ms'),'wasapi_stream_latency_ms':b.get('wasapi_stream_latency_ms'),'estimated_first_audio_ms':b.get('estimated_first_audio_ms'),'reasons':r,'promotion_pass':not r};base['ultra_low_latency_promotion_id']=hashlib.sha256(json.dumps(base,sort_keys=True,separators=(',',':')).encode()).hexdigest();Path(a.out).write_text(json.dumps(base,indent=2),encoding='utf-8');print('ULTRA LOW LATENCY PROMOTION V25','PASS' if not r else 'FAIL',base['ultra_low_latency_promotion_id'])
    if r:raise SystemExit(3)
if __name__=='__main__':main()
