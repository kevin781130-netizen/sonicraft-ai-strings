from pathlib import Path
import json
import sys

from stringcc_governance import (
    ConductorIntent, ConductorSteerer, CandidateUtilityPredictor,
    CounterfactualAuditor, EvidenceLedger, GovernedRepairOrchestrator,
)
from stringcc_governance.external_sonicraft import SonicraftExternalAdapter


def test_conductor_generates_bounded_distinct_families():
    base = {"apex_position": 0.58, "intensity_scale": 1.0}
    rows = ConductorSteerer().propose("0:0:0", base, ConductorIntent(energy=.9, tension=.8, section_role="lead"), {"density_norm": .3})
    assert {r.family for r in rows} == {"shape", "energy", "connection", "restraint"}
    assert all(0.12 <= r.overrides["apex_position"] <= 0.88 for r in rows)
    assert all(r.candidate_id.startswith("cand_") for r in rows)
    assert base == {"apex_position": 0.58, "intensity_scale": 1.0}


def test_evidence_ledger_idempotent_and_summary(tmp_path):
    ledger = EvidenceLedger(tmp_path / "evidence.jsonl")
    rec = {"candidate_id":"x", "phrase_key":"p", "family":"shape", "accepted":True, "local_gain":.03}
    a = ledger.append(rec); b = ledger.append(rec)
    assert a["evidence_id"] == b["evidence_id"]
    assert len(ledger.records()) == 1
    summary = ledger.summary()
    assert summary["families"]["shape"]["accept_rate"] == 1.0


def test_utility_predictor_learns_winning_family(tmp_path):
    ledger = EvidenceLedger(tmp_path / "e.jsonl")
    for n in range(4):
        ledger.append({"candidate_id":f"a{n}","phrase_key":"p","family":"energy","accepted":True,"local_gain":.04})
        ledger.append({"candidate_id":f"b{n}","phrase_key":"p","family":"shape","accepted":False,"local_gain":-.01})
    candidates = ConductorSteerer().propose("p", {}, ConductorIntent())
    ranked = CandidateUtilityPredictor(ledger, exploration=.01).rank(candidates)
    assert ranked[0][0].family == "energy"


def test_counterfactual_auditor_accepts_minimal_local_gain():
    audit = CounterfactualAuditor().audit(
        {"loss":.10}, {"loss":.08},
        baseline_whole={"loss":.12}, candidate_whole={"loss":.115},
        adjacent_baseline={"left":.1}, adjacent_candidate={"left":.101},
        changed_dimensions=["cc1_gain_scale","apex_position"],
    )
    assert audit.accepted
    assert audit.local_delta > 0
    assert audit.causal_confidence > 0


def test_counterfactual_auditor_rejects_spillover_and_whole_regression():
    audit = CounterfactualAuditor(max_whole_regression=.001, max_adjacent_regression=.01).audit(
        {"loss":.10}, {"loss":.07},
        baseline_whole={"loss":.12}, candidate_whole={"loss":.13},
        adjacent_baseline={"left":.1}, adjacent_candidate={"left":.13},
        changed_dimensions=["cc1_gain_scale"],
    )
    assert not audit.accepted
    assert "whole_piece_regression" in audit.reasons
    assert "adjacent_phrase_spillover" in audit.reasons


def test_governed_orchestrator_fail_closed_and_retains_evidence(tmp_path):
    ledger = EvidenceLedger(tmp_path / "ledger.jsonl")
    orch = GovernedRepairOrchestrator(ledger)
    def evaluator(c):
        if c.family == "energy":
            return {"local":{"loss":.07}, "whole":{"loss":.099}}
        return {"local":{"loss":.101}, "whole":{"loss":.10}}
    out = orch.run_phrase(
        phrase_key="p", base_overrides={}, intent=ConductorIntent(energy=.9),
        baseline={"local":{"loss":.1}, "whole":{"loss":.1}}, evaluator=evaluator,
    )
    assert out["winner"] is not None
    assert out["winner"]["family"] == "energy"
    assert len(ledger.records()) == 4


def test_external_adapter_json_process_boundary(tmp_path):
    script = tmp_path / "echo_bridge.py"
    script.write_text('''import json,sys\nfrom pathlib import Path\ni=Path(sys.argv[1]); o=Path(sys.argv[2]); p=json.loads(i.read_text()); o.write_text(json.dumps({"ok":True,"value":p["value"]+1}))\n''')
    adapter = SonicraftExternalAdapter([sys.executable, str(script), "{input}", "{output}"])
    out = adapter.run({"value":4}, workdir=tmp_path / "work")
    assert out["ok"] and out["value"] == 5
