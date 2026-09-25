#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training"))
from dnni_reference import import_four


def main():
    ap = argparse.ArgumentParser(description="Quarantine and fingerprint four user-supplied DNNI packages as separate timbre references.")
    ap.add_argument("--source", action="append", required=True, help="Path to an unpacked-DNNI .tar; pass exactly four times.")
    ap.add_argument("--name", action="append", help="Optional timbre label; pass four times.")
    ap.add_argument("--out", default="datasets/dnni_four_timbres/source")
    a = ap.parse_args()
    recs = import_four(a.source, a.out, a.name)
    print(json.dumps([asdict(x) for x in recs], indent=2, ensure_ascii=False))
    print("NOTE: source weights are quarantined/reference-only; they are not decoded PyTorch checkpoints.")


if __name__ == "__main__":
    main()
