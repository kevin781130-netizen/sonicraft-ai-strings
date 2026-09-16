# SONICRAFT AI Strings v7.0 RC2 — Special Technique Promotion Gate

## Purpose

This gate defines how currently semantic-only string techniques may become release-approved acoustic techniques without weakening the existing v7.0 feature freeze or fabricating support.

The initial gated technique set is:

- col legno
- sul ponticello
- sul tasto
- natural harmonics
- artificial harmonics
- con sordino
- portamento / transition variants

## Current truth boundary

**Semantic preservation is not acoustic support.** Until a technique passes this gate, SONICRAFT may preserve the notation/intent semantically and surface an explicit unsupported-acoustic warning, but it must not claim that the final acoustic model renders that technique faithfully.

## Promotion requirements

A technique is release-approved only when all of the following evidence is present and bound to the exact release model manifest SHA-256 and exact VST3 SHA-256:

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

Before promotion:

`notation/intent -> semantic preservation -> unsupported acoustic warning`

After promotion:

`notation/intent -> declared trained technique -> exact-model render -> blind QA evidence -> host evidence`

No source-code presence, UI control, MIDI label, or test stub is sufficient to mark a technique acoustically supported.

## v7.0 release rule

This document does not add a new performance feature to the frozen v7.0 core. It adds an evidence contract for acoustic capabilities that may only be marked supported after the final model pack exists and passes release validation.
