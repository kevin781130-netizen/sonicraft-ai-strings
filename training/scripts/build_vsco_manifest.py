from __future__ import annotations
import argparse, json, re
from pathlib import Path

INST_PATTERNS = {
    "violin": ("solo violin", "violin"),
    "viola": ("solo viola", "viola"),
    "cello": ("solo cello", "cello", "violoncello"),
}
ART = [
    ("flaut", "flautando"), ("harm", "harmonic"), ("trem", "tremolo"),
    ("pizz", "pizzicato"), ("spicc", "spiccato"), ("stacc", "staccato"),
    ("marc", "marcato"), ("leg", "legato"), ("sus", "sustain"),
]
NOTE_RE = re.compile(r"(?<![A-Za-z])([A-Ga-g])([#b]?)(-?\d)(?!\d)")
PC = {"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}

def guess_inst(path: Path):
    s=str(path).replace("_"," ").replace("-"," ").lower()
    # avoid violin falsely matching violoncello: test longer/specific family names first
    if "viola" in s: return "viola"
    if "cello" in s or "violoncello" in s: return "cello"
    if "violin" in s: return "violin"
    return None

def guess_art(path: Path):
    s=str(path).lower()
    for key,val in ART:
        if key in s: return val
    return "unknown"

def note_to_midi(path: Path):
    m=NOTE_RE.search(path.stem)
    if not m: return None
    n,acc,octv=m.groups(); pc=PC[n.upper()] + (1 if acc=="#" else -1 if acc=="b" else 0)
    return (int(octv)+1)*12+pc

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    root=Path(a.root); rows=[]
    for p in root.rglob('*'):
        if p.suffix.lower() not in {'.wav','.flac','.aif','.aiff'}: continue
        inst=guess_inst(p)
        if not inst: continue
        rows.append({
            'audio':str(p.resolve()), 'dataset':'vsco2_ce', 'instrument':inst,
            'articulation':guess_art(p), 'midi_note':note_to_midi(p),
            'release_blocked':False, 'license':'CC0-1.0',
            'training_role':'articulation_control_pretrain', 'final_timbre_anchor':False
        })
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')
    print(f'wrote {len(rows)} VSCO2 string files -> {out}')
    if not rows: raise SystemExit('No violin/viola/cello audio found; verify repository layout/version.')
if __name__=='__main__': main()
