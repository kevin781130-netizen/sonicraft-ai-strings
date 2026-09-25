#!/usr/bin/env python3
from __future__ import annotations
"""Run existing renderer/distillation entries while bypassing *commercial* source gating only.

This wrapper is intentionally named RESEARCH and refuses to touch release/promotion code.
The input must carry dedicated DNNI-research identity markers.
"""
import argparse, importlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'training'))


def research_validate(index_path, registry_path=None):
    rows=[json.loads(x) for x in Path(index_path).read_text(encoding='utf-8').splitlines() if x.strip()]
    if not rows: raise RuntimeError('research index is empty')
    bad=[]
    for r in rows:
        dataset=str(r.get('dataset',''))
        source_kind=str(r.get('source_kind',''))
        if not dataset.startswith('dnni_research_timbre_'):
            bad.append(f'unexpected dataset={dataset!r}')
        if source_kind != 'proprietary_teacher_render_research_only':
            bad.append(f'unexpected source_kind={source_kind!r}')
        if r.get('cleanroom_eligible',False):
            bad.append('unexpected cleanroom_eligible=true')
    if bad: raise RuntimeError('DNNI research wrapper only accepts explicitly tagged DNNI research rows: '+str(bad[:5]))
    return len(rows)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('entry',choices=('renderer','distill','shortcut'));ap.add_argument('args',nargs=argparse.REMAINDER)
    a=ap.parse_args(); modname={'renderer':'train_ballad_renderer','distill':'distill_renderer','shortcut':'shortcut_distill_renderer'}[a.entry]
    mod=importlib.import_module(modname)
    mod.validate_index=research_validate
    forwarded=list(a.args)
    if forwarded and forwarded[0]=='--': forwarded=forwarded[1:]
    sys.argv=[modname+'.py']+forwarded
    print('[RESEARCH ONLY] commercial source gate bypassed for this process; input is restricted to dnni_research_timbre_* / proprietary_teacher_render_research_only rows.')
    mod.main()

if __name__=='__main__':main()
