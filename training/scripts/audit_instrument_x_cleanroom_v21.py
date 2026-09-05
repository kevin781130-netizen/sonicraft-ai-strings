from __future__ import annotations
import argparse, json
from pathlib import Path

# This audit is intentionally conservative. It does not try to infer copyright status from names;
# it blocks artifact classes that should never be present in this clean-room source package.
BANNED_SUFFIXES={'.amdata','.aaxplugin','.component'}
BANNED_NAMES={
    'instrument x.vst3','instrument x.dll','instrument x.exe','instrumentx.vst3',
    'dreamtonics instrument x.vst3','instrument x preset','instrument x model'
}
ALLOWED_TEXT_EXT={'.py','.cpp','.h','.md','.txt','.json','.ps1','.bat','.iss','.xml','.uidesc','.cmake'}

def audit(root:Path):
    violations=[]; checked=0
    for p in root.rglob('*'):
        if not p.is_file(): continue
        checked+=1; low=p.name.lower()
        if p.suffix.lower() in BANNED_SUFFIXES or low in BANNED_NAMES:
            violations.append(str(p.relative_to(root)))
        # No competitor binaries or model containers may be parked under third_party/source/reference dirs.
        parts={x.lower() for x in p.parts}
        if ('instrument_x' in parts or 'instrument-x' in parts or 'dreamtonics' in parts) and p.suffix.lower() not in ALLOWED_TEXT_EXT:
            violations.append(str(p.relative_to(root)))
    report={'schema':1,'policy':'public-behavior-only-clean-room-v21','checked_files':checked,
            'violations':sorted(set(violations)),'pass':not violations,
            'forbidden_inputs':['competitor code','competitor binaries','competitor model weights','competitor presets','competitor rendered training corpus','decompiled/disassembled material','private room measurements']}
    return report

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); ap.add_argument('--report'); a=ap.parse_args()
    r=audit(Path(a.root).resolve())
    if a.report: Path(a.report).write_text(json.dumps(r,indent=2),encoding='utf-8')
    print('v2.1 CLEAN-ROOM AUDIT', 'PASS' if r['pass'] else 'BLOCKED', 'checked',r['checked_files'])
    for v in r['violations']: print(' -',v)
    raise SystemExit(0 if r['pass'] else 2)
if __name__=='__main__': main()
