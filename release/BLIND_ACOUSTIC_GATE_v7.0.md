# SONICRAFT AI Strings v7.0 RC2 — Blind Acoustic Release Gate

## Purpose

The final RTX/model render gate proves that the exact approved model can render reproducibly enough for release verification on the target machine. It does not, by itself, prove that the resulting strings are perceptually competitive with real performers or that a requested special technique is audibly identifiable.

For v7.0 commercial approval, blind acoustic evidence is therefore a separate release input.

## Required evidence file

`release/rc_evidence/blind-acoustic-qa.json`

The file is generated from an external listening study and must refer to the exact final release artifacts.

Required top-level fields:

- `schema`: `1`
- `product`: `SONICRAFT AI Strings Q4`
- `release`: `7.0.0-rc2`
- `overall`: `PASS`
- `plugin_sha256`: SHA-256 of the exact release VST3 binary
- `model_manifest_sha256`: SHA-256 of the exact approved release model manifest
- `protocol_sha256`: SHA-256 of the frozen listening-test protocol
- `raw_results_sha256`: SHA-256 of the raw listener-result export
- `protocol.double_blind`: `true`
- `protocol.randomized`: `true`
- `protocol.negative_control`: `true`
- `protocol.listener_count`: positive integer
- `protocol.trial_count`: positive integer
- `results.realism.status`: `PASS`
- `results.technique_identity.status`: `PASS`

The gate does not invent or retroactively choose statistical thresholds. The frozen protocol referenced by `protocol_sha256` must define the acceptance criteria before the release study is scored.

## Separation of claims

- RTX/model checkpoint verification answers: **Did the exact model and runtime render the bound test correctly?**
- Blind acoustic QA answers: **Did blinded listeners accept the final acoustic result under the frozen protocol?**
- Special Technique Promotion answers: **Are specific extended techniques both trained and audibly identifiable?**

All three are required for their respective release claims. None may substitute for another.

## Fail-closed rule

`FINAL_GATE_V70` must remain blocked when blind acoustic evidence is missing, malformed, not PASS, or bound to a different VST3/model-manifest hash.

This gate does not claim that any blind listening study has already passed.
