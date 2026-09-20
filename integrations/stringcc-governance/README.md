# StringCC Governance Bridge v1.1

Optional clean-room integration layer for **SONICRAFT AI Strings** and StringCC.

This integration intentionally does **not** copy or import SONICRAFT source code. It is a separately MIT-licensed governance bridge that keeps the two projects separated by a JSON/subprocess boundary while exposing the orchestration ideas needed by StringCC:

- conductor intent / phrase steering
- governed candidate families: `shape`, `energy`, `connection`, `restraint`
- evidence-driven candidate utility ranking
- fail-closed counterfactual audit
- append-only evidence ledger
- optional external JSON process adapter

## Licensing and process boundary

The reviewed SONICRAFT baseline is `main@4f9f1915d6179ffb3d669bbb3a483c4e30643fbf` (Q4 v7.0 RC2). At the original integration review time, no top-level SONICRAFT project license file was present, so the bridge was deliberately implemented as a clean-room/process-boundary component.

The repository now carries an explicit proprietary project-level `LICENSE` for SONICRAFT-owned materials. This **does not change the bridge license**: `integrations/stringcc-governance/` remains MIT licensed under its own `LICENSE`, while SONICRAFT source, models, assets and product binaries remain outside that MIT grant.

The bridge is an optional developer interoperability component. It is not copied into the commercial SONICRAFT VST3/prebuilt consumer payload.

## Install / test

```bash
python -m pip install -e .
pytest -q
```

## CLI

```bash
stringcc-governance plan 0:0:0 --intent examples/demo_governance_intent.json
```

See `docs/SONICRAFT_FUSION_AUDIT_ZH.md` and `docs/SONICRAFT_INTEGRATION_NOTICE.md` for the original integration decision and historical review context. See the repository-level `docs/COMMERCIAL_RELEASE_READINESS_v7.0_RC2.md` for the current commercial release boundary.
