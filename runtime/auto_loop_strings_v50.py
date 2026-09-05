"""SONICRAFT v5.0 fully local Shadow Render -> Audio Judge -> Repair Policy auto-loop."""
from __future__ import annotations
from pathlib import Path
import argparse,json,shutil,sys,time

from compile_musicxml_strings_v50 import compile_file
from shadow_render_auto_v50 import start_shadow_service_v50,render_midi_v50
from audio_io_v49 import load_render_set_v49
from midi_judge_adapter_v49 import midi_to_judge_events_v49
from audio_take_judge_v37 import judge_take,score_dict
from string_repair_policy_v49 import RepairPolicyMemoryV49

SLOTS='ABCD'
MAX_ROUND=6

def _judge_round(queue_path):
    queue_path=Path(queue_path);q=json.loads(queue_path.read_text(encoding='utf-8'));qdir=queue_path.parent
    paths={s:qdir/q['slots'][s]['expected_render'] for s in SLOTS}
    audios,sr,frames=load_render_set_v49([paths[s] for s in SLOTS])
    scores={}
    for slot,audio in zip(SLOTS,audios):
        midi=qdir/q['slots'][slot]['midi'];events=midi_to_judge_events_v49(midi,sr,frames)
        scores[slot]=judge_take(audio,sr,events,0,frames)
    ranking=sorted(SLOTS,key=lambda s:scores[s].overall,reverse=True)
    winner,runner=ranking[0],ranking[1];margin=float(scores[winner].overall-scores[runner].overall)
    return q,paths,sr,frames,scores,winner,runner,margin

def _copy_decision_artifacts(src_score,out_dir,round_index,winner,queue,paths,accepted):
    qdir=Path(out_dir);midi=qdir/queue['slots'][winner]['midi'];wav=paths[winner]
    stem=Path(src_score).stem
    label='WINNER' if accepted else 'REVIEW_BEST'
    mo=qdir/f'{stem}_SONICRAFT_STRINGS_v50_{label}.mid';wo=qdir/f'{stem}_SONICRAFT_STRINGS_v50_{label}.wav'
    shutil.copy2(midi,mo);shutil.copy2(wav,wo)
    return mo,wo

def run_auto_loop_v50(score,out_dir=None,policy_path=None,host='127.0.0.1',port=49337,backend='auto',model_dir=None,cache_dir=None,mock=False,max_round=MAX_ROUND,sample_rate=48000,chunk_seconds=40.0,overlap_seconds=.75):
    score=Path(score).resolve()
    if not score.exists():raise FileNotFoundError(score)
    out_dir=Path(out_dir) if out_dir else score.with_name(score.stem+'_SONICRAFT_v50_AUTO')
    out_dir.mkdir(parents=True,exist_ok=True)
    max_round=max(1,min(MAX_ROUND,int(max_round)))
    policy_path=Path(policy_path) if policy_path else None
    spawned=None;trace=[];final=None
    start=time.time()
    try:
        spawned,service_status=start_shadow_service_v50(host,port,mock,backend,model_dir,cache_dir)
        for round_index in range(1,max_round+1):
            out=out_dir/(score.stem+f'_SONICRAFT_STRINGS_v50_R{round_index}.mid')
            comp=compile_file(score,out,policy_path,round_index)
            queue_path=Path(comp['judge_queue_json']);queue=json.loads(queue_path.read_text(encoding='utf-8'))
            render_info={}
            try:
                for si,slot in enumerate(SLOTS):
                    midi=out_dir/queue['slots'][slot]['midi'];wav=out_dir/queue['slots'][slot]['expected_render']
                    render_info[slot]=render_midi_v50(midi,wav,host,port,sample_rate,chunk_seconds,overlap_seconds,request_seed=500000+round_index*100+si*10)
            except Exception as ex:
                trace.append({'round':round_index,'phase':'render','status':'failed','error':f'{type(ex).__name__}: {ex}','renders':render_info})
                final={'status':'render_failed','round':round_index,'error':f'{type(ex).__name__}: {ex}'}
                break

            q,paths,sr,frames,scores,winner,runner,margin=_judge_round(queue_path)
            mem=RepairPolicyMemoryV49(q['policy_path']);before=mem.snapshot()
            stale=(before.generation!=int(q['policy_generation']) or before.profile_hash!=str(q['policy_hash']))
            ws=scores[winner]
            if stale:learn={'learned':False,'reason':'stale_policy'}
            else:learn=mem.learn(winner,margin,ws.safety,ws.overall)
            after=mem.snapshot()
            gate_accepted=bool(learn.get('learned'))
            row={
                'round':round_index,'phase':'judge','status':'ok','structural_recommendation':q.get('structural_recommendation'),
                'audio_winner':winner,'runner_up':runner,'margin':round(margin,9),
                'scores':{s:score_dict(scores[s]) for s in SLOTS},'renders':{s:{k:(str(v) if isinstance(v,Path) else v) for k,v in render_info[s].items()} for s in SLOTS},
                'policy_before':{'generation':before.generation,'hash':before.profile_hash,'confidence':before.confidence,'values':before.values},
                'learning':{'accepted':gate_accepted,'reason':learn.get('reason'),'winner_safety':ws.safety,'winner_overall':ws.overall},
                'policy_after':{'generation':after.generation,'hash':after.profile_hash,'confidence':after.confidence,'values':after.values},
            }
            trace.append(row)

            # Stop conditions are explicit and conservative.
            if not gate_accepted:
                midi,wav=_copy_decision_artifacts(score,out_dir,round_index,winner,q,paths,False)
                final={'status':'review_required','reason':learn.get('reason'),'round':round_index,'best_current':winner,'midi':str(midi),'wav':str(wav),'margin':margin}
                break
            if round_index>=max_round:
                midi,wav=_copy_decision_artifacts(score,out_dir,round_index,winner,q,paths,True)
                final={'status':'round_cap','round':round_index,'winner':winner,'midi':str(midi),'wav':str(wav),'margin':margin}
                break
            # Accepted learning continues: compile next round from the now-updated persistent policy.
        if final is None:
            final={'status':'internal_no_final'}
    finally:
        if spawned is not None:
            try:spawned.terminate();spawned.wait(timeout=4)
            except Exception:
                try:spawned.kill()
                except Exception:pass

    report={
        'schema':1,'version':'5.0','source_score':str(score),'out_dir':str(out_dir.resolve()),
        'service':{'host':host,'port':int(port),'backend':backend,'mock':bool(mock)},
        'max_round':max_round,'sample_rate':int(sample_rate),'chunk_seconds':float(chunk_seconds),'overlap_seconds':float(overlap_seconds),
        'elapsed_seconds':round(time.time()-start,3),'rounds':trace,'final':final,
        'authority_note':'Objective Audio Judge may tune bounded Repair Policy only. Personal Judge Memory and acoustic model remain separate.',
    }
    rp=out_dir/(score.stem+'_SONICRAFT_STRINGS_v50_DECISION_TRACE.json');rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report,rp

def main(argv=None):
    ap=argparse.ArgumentParser(description='SONICRAFT v5.0 fully local Shadow Render / Judge / Repair auto-loop.')
    ap.add_argument('score',type=Path);ap.add_argument('--out-dir',type=Path);ap.add_argument('--policy',type=Path)
    ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=49337);ap.add_argument('--backend',choices=['auto','torch','ort'],default='auto')
    ap.add_argument('--model-dir',type=Path);ap.add_argument('--cache-dir',type=Path);ap.add_argument('--mock',action='store_true')
    ap.add_argument('--max-round',type=int,default=6);ap.add_argument('--sample-rate',type=int,default=48000);ap.add_argument('--chunk-seconds',type=float,default=40.0);ap.add_argument('--overlap-seconds',type=float,default=.75)
    a=ap.parse_args(argv)
    try:r,rp=run_auto_loop_v50(a.score,a.out_dir,a.policy,a.host,a.port,a.backend,a.model_dir,a.cache_dir,a.mock,a.max_round,a.sample_rate,a.chunk_seconds,a.overlap_seconds)
    except Exception as ex:
        print('ERROR:',ex,file=sys.stderr);return 2
    print('SONICRAFT v5.0 Local Shadow Auto-Loop finished')
    print('Final:',json.dumps(r['final'],ensure_ascii=False))
    print('Decision trace:',rp)
    return 0 if r['final'].get('status') not in ('render_failed','internal_no_final') else 3
if __name__=='__main__':raise SystemExit(main())
