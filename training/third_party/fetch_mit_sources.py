#!/usr/bin/env python3
"""Fetch pinned permissive source modules without bundling third-party datasets/checkpoints.

Core package stays tiny. Run on a development/training machine only.
"""
from __future__ import annotations
import argparse, fnmatch, json, shutil, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "training" / "third_party" / "mit_sources.lock.json"
DEST = ROOT / "training" / "third_party" / "vendor"

def run(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)

def allowed(path: str, includes: list[str], excludes: list[str]) -> bool:
    if any(fnmatch.fnmatch(path, p) for p in excludes):
        return False
    return any(fnmatch.fnmatch(path, p) for p in includes)

def fetch_one(src: dict, force=False):
    out = DEST / src["id"]
    if out.exists():
        if not force:
            print(f"[skip] {src['id']} already exists")
            return
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"sonicraft_{src['id']}_") as td:
        td = Path(td)
        run("git", "clone", "--filter=blob:none", "--no-checkout", src["repo"], str(td / "repo"))
        repo = td / "repo"
        commit = src["commit"]
        if commit != "HEAD":
            run("git", "checkout", "--detach", commit, cwd=repo)
        else:
            run("git", "checkout", "--detach", cwd=repo)
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        for p in repo.rglob("*"):
            if not p.is_file() or ".git" in p.parts:
                continue
            rel = p.relative_to(repo).as_posix()
            if allowed(rel, src["include"], src.get("exclude_globs", [])):
                target = out / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)
        (out / "SONICRAFT_VENDOR_META.json").write_text(json.dumps({
            "id": src["id"], "repo": src["repo"], "requested_commit": commit,
            "actual_commit": actual, "license": src["license"], "purpose": src["purpose"]
        }, indent=2), encoding="utf-8")
        license_files = [out / name for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING") if (out / name).exists()]
        if not license_files:
            raise RuntimeError(f"{src['id']}: no license file was captured; refusing vendor import")
        print(f"[ok] {src['id']} @ {actual}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", help="source ids; empty = all")
    ap.add_argument("--force", action="store_true")
    a=ap.parse_args()
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    wanted=set(a.ids)
    for src in lock["sources"]:
        if wanted and src["id"] not in wanted: continue
        fetch_one(src, a.force)

if __name__ == "__main__": main()
