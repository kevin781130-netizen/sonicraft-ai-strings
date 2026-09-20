# SONICRAFT AI Strings v7.0 RC2 — Final Model Manifest Contract

## Purpose

A model file hash proves artifact identity, not commercial provenance. Before `FINAL_GATE_V70` or `PUBLIC_RELEASE_GATE_V70` can approve a release candidate, the final model pack must therefore pass an independent provenance gate.

## Required final manifest

The release model pack must contain:

`release/prebuilt/Models/release_model_manifest.json`

The manifest must identify `SONICRAFT AI Strings Q4`, release `7.0.0-rc2`, declare `commercial_safe=true` and `release_approved=true`, and set:

`training_data_rights_status = approved_for_commercial_training_and_distribution`

## Required provenance hashes

The manifest `provenance` object must contain valid SHA-256 values for:

- dataset manifest;
- training-run manifest;
- model card;
- rights review;
- final checkpoint.

It must also record a concrete training-run ID, approver, and approval timestamp.

These hashes bind the shipped model to the evidence used to approve it. They do not replace the underlying records; those records must remain retained in the release evidence archive or approved internal provenance store.

## Model files

Every shipped model file must be listed by relative name and SHA-256. `FINAL_MODEL_GATE_V70.bat` verifies each listed file against the final model directory.

## Capability truth boundary

`capabilities.special_techniques` must explicitly classify each declared technique as one of:

- `trained`
- `semantic_only`
- `unsupported`

A final model may still ship with a special technique classified as `semantic_only` or `unsupported`. Such a technique must not be advertised as acoustically supported unless the separate Special Technique Promotion Gate passes.

## Release integration

Both `FINAL_GATE_V70.bat` and `PUBLIC_RELEASE_GATE_V70.bat` run `FINAL_MODEL_GATE_V70.bat` before the existing host/acoustic/signing final gate.

This contract does not claim that a final trained model currently exists or has been approved.
