# StringCC Governance Bridge v1.1

Optional clean-room integration layer for **SONICRAFT AI Strings** and StringCC.

This PR intentionally does **not** copy or import SONICRAFT source code. It adds a small MIT-licensed governance bridge that keeps the two projects separated by a JSON/subprocess boundary while exposing the useful orchestration ideas needed by StringCC:

- conductor intent / phrase steering
- governed candidate families: `shape`, `energy`, `connection`, `restraint`
- evidence-driven candidate utility ranking
- fail-closed counterfactual audit
- append-only evidence ledger
- optional external JSON process adapter

## Why process-boundary integration

The reviewed SONICRAFT baseline is `main@4f9f1915d6179ffb3d669bbb3a483c4e30643fbf` (Q4 v7.0 RC2). At review time, no top-level project `LICENSE`, `LICENSE.md`, or `COPYING` file was found that clearly grants a source license for SONICRAFT-owned code. This bridge therefore keeps implementation and licensing boundaries explicit.

## Install / test

```bash
python -m pip install -e .
pytest -q
```

## CLI

```bash
stringcc-governance plan 0:0:0 --intent examples/demo_governance_intent.json
```

See `docs/SONICRAFT_FUSION_AUDIT_ZH.md` and `docs/SONICRAFT_INTEGRATION_NOTICE.md` for the integration decision and license boundary.
