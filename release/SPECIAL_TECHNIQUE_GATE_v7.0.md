# SONICRAFT AI Strings v7.0 RC2 — Special Technique Promotion Gate

## Purpose

This gate defines how special string techniques may become release-approved acoustic techniques without weakening the existing v7.0 feature freeze or fabricating support.

The initial gated technique set is:

- col legno
- sul ponticello
- sul tasto
- natural harmonics
- artificial harmonics
- con sordino
- portamento / transition variants

## Current truth boundary

**Semantic preservation is not acoustic support.** Exact semantic support is itself a prerequisite: the frozen score/runtime path must preserve the identity of the requested technique before that technique can be promoted acoustically.

The current parser truth is intentionally narrower than the gated target set:

- `col legno`, `sul ponticello`, and `sul tasto` are preserved as direction-derived technical metadata plus explicit unsupported-technique warnings;
- MusicXML `glissando` / `slide` map to the existing Portamento path;
- MusicXML `harmonic` maps to one generic Harmonic articulation, but the natural/artificial distinction is not preserved;
- `con sordino` currently has no dedicated semantic token/warning in the frozen parser.

Therefore generic harmonic recognition must not be presented as exact natural-harmonic or artificial-harmonic support, and unparsed mute text must not be presented as con-sordino semantic support.

## Promotion requirements

**Exact semantic support must exist before acoustic promotion.** A technique is release-approved only when semantic support is true and all of the following evidence is present and bound to the exact release model manifest SHA-256 and exact VST3 SHA-256:

1. **Rights-cleared training/evaluation material**
   - provenance recorded;
   - performer/instrument/session metadata recorded;
   - no ambiguous or non-commercial source is used for a commercial promotion claim.

2. **Technique annotation integrity**
   - technique label is explicit at phrase or note level;
   - transition boundaries are represented;
   - dynamic context and neighboring articulation context are retained.

3. **Model coverage**
   - the approved release model manifest explicitly declares the technique;
   - the runtime maps only to a trained/declared technique ID;
   - no fallback ID is relabeled as if it were the requested technique.

4. **Render verification**
   - deterministic test score/cue exists;
   - rendered artifact hashes are recorded;
   - failure to produce the requested technique is fail-closed.

5. **Blind acoustic review**
   - technique identity is judged separately from overall realism;
   - comparison includes at least a normal-articulation negative control;
   - acceptance result is stored as evidence, not inferred from implementation presence.

6. **Host validation**
   - Cubase and Studio One can load, automate, save/reopen, and render the technique path without state corruption;
   - evidence is tied to the same release binary hash.

## Release behavior

When exact semantics exist but acoustic promotion does not:

`notation/intent -> semantic preservation -> explicit unsupported-acoustic state`

When exact semantics do not yet exist:

`notation/intent -> no exact technique claim -> semantic gap remains open`

After promotion:

`notation/intent -> exact semantic identity -> declared trained technique -> exact-model render -> blind QA evidence -> host evidence`

No source-code presence, UI control, MIDI label, generic parent articulation, or test stub is sufficient to mark a technique acoustically supported.

## Executable semantic audit

`scripts/special_technique_semantic_audit_v70.py` runs small MusicXML fixtures through the actual frozen parser and compares observed semantics with `release/special_technique_status_v7.0.json`. This keeps the machine-readable truth boundary tied to implementation rather than documentation alone.

## v7.0 release rule

This document does not add a new performance feature to the frozen v7.0 core. It adds evidence and truth contracts for capabilities that may only be marked supported after the semantic path, final model pack, acoustic evidence, and host validation all agree.
