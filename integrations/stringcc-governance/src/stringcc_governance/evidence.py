from __future__ import annotations
from pathlib import Path
from typing import Any, Iterable
import json
import time
from .models import stable_id


class EvidenceLedger:
    """Append-only JSONL evidence ledger for candidate provenance and learning."""
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        with self.path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid governance ledger JSONL line {line_no}: {exc}") from exc
                out.append(rec)
        return out

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        rec = dict(record)
        rec.setdefault("schema", "stringcc.governance.evidence.v1")
        rec.setdefault("timestamp", time.time())
        rec.setdefault("evidence_id", stable_id("ev", {k: v for k, v in rec.items() if k not in {"timestamp", "evidence_id"}}))
        # Idempotence protects resumed optimization jobs from duplicating credit.
        existing = {str(r.get("evidence_id")) for r in self.records()}
        if str(rec["evidence_id"]) in existing:
            return rec
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        return rec

    def query(self, *, phrase_key: str | None = None, family: str | None = None, accepted: bool | None = None) -> list[dict[str, Any]]:
        out = []
        for r in self.records():
            if phrase_key is not None and str(r.get("phrase_key")) != str(phrase_key):
                continue
            if family is not None and str(r.get("family")) != str(family):
                continue
            if accepted is not None and bool(r.get("accepted")) != bool(accepted):
                continue
            out.append(r)
        return out

    def summary(self) -> dict[str, Any]:
        rows = self.records(); fam: dict[str, dict[str, float]] = {}
        for r in rows:
            name = str(r.get("family", "unknown")); bucket = fam.setdefault(name, {"trials": 0, "accepted": 0, "mean_gain": 0.0})
            bucket["trials"] += 1
            bucket["accepted"] += int(bool(r.get("accepted", False)))
            bucket["mean_gain"] += float(r.get("local_gain", 0.0) or 0.0)
        for b in fam.values():
            b["mean_gain"] = b["mean_gain"] / max(1, int(b["trials"]))
            b["accept_rate"] = b["accepted"] / max(1, int(b["trials"]))
        return {"schema": "stringcc.governance.summary.v1", "records": len(rows), "families": fam}
