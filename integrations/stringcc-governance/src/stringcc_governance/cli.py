from __future__ import annotations
import argparse
import json
from pathlib import Path
from .models import ConductorIntent, CandidateProposal
from .conductor import ConductorSteerer
from .evidence import EvidenceLedger
from .utility import CandidateUtilityPredictor
from .audit import CounterfactualAuditor
from .external_sonicraft import SonicraftExternalAdapter


def _json(path: str) -> dict:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict): raise ValueError(f"Expected JSON object: {path}")
    return obj


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="stringcc-governance", description="Clean-room Sonicraft-inspired governance layer")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("plan", help="Generate and evidence-rank governed phrase candidates")
    sp.add_argument("phrase_key"); sp.add_argument("--base"); sp.add_argument("--intent"); sp.add_argument("--features"); sp.add_argument("--ledger"); sp.add_argument("-o", "--output")
    sa = sub.add_parser("audit", help="Counterfactual audit of baseline vs candidate feedback JSON")
    sa.add_argument("baseline"); sa.add_argument("candidate"); sa.add_argument("--changed", default=""); sa.add_argument("-o", "--output")
    ss = sub.add_parser("summary", help="Summarize retained governance evidence")
    ss.add_argument("ledger")
    se = sub.add_parser("external", help="Call a separately installed Sonicraft-compatible JSON process")
    se.add_argument("payload"); se.add_argument("--command", required=True); se.add_argument("--workdir"); se.add_argument("-o", "--output")
    args = p.parse_args(argv)

    if args.cmd == "plan":
        base = _json(args.base) if args.base else {}
        intent = ConductorIntent(**(_json(args.intent) if args.intent else {})).clamped()
        features = _json(args.features) if args.features else {}
        ledger = EvidenceLedger(args.ledger) if args.ledger else None
        ranked = CandidateUtilityPredictor(ledger).rank(ConductorSteerer().propose(args.phrase_key, base, intent, features))
        data = {"schema":"stringcc.governance.plan.v1", "phrase_key":args.phrase_key, "intent":intent.__dict__, "candidates":[{"proposal":c.to_dict(),"utility":u} for c,u in ranked]}
    elif args.cmd == "audit":
        b, c = _json(args.baseline), _json(args.candidate)
        data = CounterfactualAuditor().audit(b.get("local", b), c.get("local", c), baseline_whole=b.get("whole"), candidate_whole=c.get("whole"), adjacent_baseline=b.get("adjacent"), adjacent_candidate=c.get("adjacent"), changed_dimensions=[x for x in args.changed.split(",") if x]).to_dict()
    elif args.cmd == "summary":
        data = EvidenceLedger(args.ledger).summary()
    else:
        data = SonicraftExternalAdapter(args.command).run(_json(args.payload), workdir=args.workdir)
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    if getattr(args, "output", None): Path(args.output).write_text(text+"\n", encoding="utf-8")
    else: print(text)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
