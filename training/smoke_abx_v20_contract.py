from __future__ import annotations
"""Dependency-light regression smoke for blind ABX packet + v20 scoring."""
import csv,json,subprocess,sys,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'training'/'scripts'


def run(args:list[str],expected=0):
    p=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    if p.returncode!=expected:
        raise AssertionError(f'command returned {p.returncode}, expected {expected}: {args}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}')
    return p


def main():
    with tempfile.TemporaryDirectory() as td:
        d=Path(td);real=d/'real';gen=d/'generated';packet=d/'packet';responses=d/'responses'
        real.mkdir();gen.mkdir();responses.mkdir()
        for i in range(20):
            stem=f'clip_{i:02d}'
            (real/(stem+'.wav')).write_bytes(b'RIFF-real-'+bytes([i]))
            (gen/(stem+'.wav')).write_bytes(b'RIFF-generated-'+bytes([i]))

        run([sys.executable,str(SCRIPTS/'prepare_blind_abx.py'),'--real-dir',str(real),'--generated-dir',str(gen),'--out',str(packet),'--min-trials','20','--seed','260917'])
        run([sys.executable,str(SCRIPTS/'validate_blind_abx_packet.py'),'--packet',str(packet),'--min-trials','20'])

        key_path=packet/'private'/'answer_key.json';key=json.loads(key_path.read_text(encoding='utf-8'))
        assert key['schema']==2 and len(key['answers'])==20 and len(key['trials'])==20
        truth={x['trial_id']:x['answer'] for x in key['answers']}
        template=packet/'public'/'responses.csv'
        with template.open(newline='',encoding='utf-8-sig') as f:
            reader=csv.DictReader(f);rows=list(reader);fields=list(reader.fieldnames or [])
        assert 'listener_id' in fields and 'pick_generated' in fields

        for li in range(5):
            out=responses/f'listener_{li+1}.csv'
            with out.open('w',newline='',encoding='utf-8-sig') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
                for idx,row in enumerate(rows):
                    r=dict(row);ans=truth[r['trial_id']]
                    # Exactly chance: ten correct and ten incorrect per listener.
                    r['listener_id']=''  # scorer should derive ID from filename
                    r['pick_generated']=ans if idx<10 else ('B' if ans=='A' else 'A')
                    w.writerow(r)

        score=d/'score.json'
        run([sys.executable,str(SCRIPTS/'score_abx_v20.py'),'--key',str(key_path),'--responses',str(responses),'--out',str(score)])
        result=json.loads(score.read_text(encoding='utf-8'))
        assert result['transparency_pass'] is True
        assert result['listener_count']==5 and result['trial_count']==100 and abs(result['accuracy']-.5)<1e-9

        legacy=d/'legacy_key.json';legacy.write_text(json.dumps({'schema':1,'trials':key['trials']},indent=2),encoding='utf-8')
        legacy_score=d/'legacy_score.json'
        run([sys.executable,str(SCRIPTS/'score_abx_v20.py'),'--key',str(legacy),'--responses',str(responses),'--out',str(legacy_score)])
        old=json.loads(legacy_score.read_text(encoding='utf-8'))
        assert old['transparency_pass'] is True and old['listener_count']==5 and old['trial_count']==100

    print('blind ABX v20 contract smoke: PASS')

if __name__=='__main__':main()
