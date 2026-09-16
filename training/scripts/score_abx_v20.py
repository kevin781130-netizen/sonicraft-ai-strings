from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blind_abx_v20 import score_abx_v20


def _rows_from_file(p:Path):
    rows=[]
    if p.suffix.lower()=='.csv':
        with p.open(newline='',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
    else:
        rows=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
    # A directory of one-file-per-listener responses is the preferred collection
    # format. If the template listener_id was left blank, derive a stable ID from
    # the response filename so five separate listener files cannot collapse into
    # one anonymous listener.
    for r in rows:
        if not str(r.get('listener_id') or '').strip(): r['listener_id']=p.stem
    return rows


def load_responses(path:Path):
    if path.is_dir():
        files=sorted([p for p in path.iterdir() if p.is_file() and p.suffix.lower() in ('.csv','.jsonl','.ndjson')])
        if not files: raise SystemExit(f'no response CSV/JSONL files found in {path}')
        out=[]
        for p in files: out.extend(_rows_from_file(p))
        return out,files
    if not path.is_file(): raise SystemExit(f'responses path missing: {path}')
    return _rows_from_file(path),[path]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--key',required=True);ap.add_argument('--responses',required=True,help='One response file or a directory of per-listener CSV/JSONL files.');ap.add_argument('--out',required=True);ap.add_argument('--target-max-accuracy',type=float,default=.60);ap.add_argument('--min-listeners',type=int,default=5);ap.add_argument('--min-total-trials',type=int,default=60);a=ap.parse_args()
    key=json.loads(Path(a.key).read_text(encoding='utf-8'));rows,files=load_responses(Path(a.responses))
    r=score_abx_v20(key,rows,target_max_accuracy=a.target_max_accuracy,min_listeners=a.min_listeners,min_total_trials=a.min_total_trials)
    r['response_files']=[str(p) for p in files]
    Path(a.out).write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));raise SystemExit(0 if r['transparency_pass'] else 2)

if __name__=='__main__':main()
