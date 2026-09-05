# SONICRAFT v5.3 Long-Form Conductor Intent / Section Character Lock

## Why this layer exists

Local repair can be technically correct and globally coherent yet still flatten or misplace the musical arc. A phrase before the climax may become too intense, or a release may accidentally turn into another build.

v5.3 extracts a stable macro plan from D Original before local optimization.

## Section segmentation

The score is divided into a small number of macro sections, normally 2–8. Boundaries are aligned to note/phrase onsets where possible and respect a minimum macro duration.

This is not formal musical-form recognition. Labels such as Intro, Build and Climax are deterministic performance-envelope labels.

## Extracted intent

For every macro section:
- Dynamic mean / peak / ceiling
- Vibrato depth / rate
- Bow pressure / reserve floor
- Desk looseness
- Transition density / treatment
- Per-part Lead / Inner / Foundation proportions

Whole-piece:
- intended climax section
- normalized climax position
- global Dynamic ceiling
- Vibrato palette center/spread
- Desk looseness center
- deterministic intent hash

## Baseline behavior

The target is always derived from D Original.

Repair Policy changes only A/B/C candidate behavior. Therefore the conductor intent and hash remain stable unless the underlying score/performance baseline changes.

## Macro locks

### Climax lock
A non-climax section cannot become a materially stronger climax when the original hierarchy was clear.

### Dynamic ceiling lock
Pre-/post-climax sections cannot exceed the intended climax ceiling by a meaningful amount.

### Long-line direction lock
A meaningful original build/release direction cannot reverse after local repair.

### Role lock
Strong Lead/Foundation assignments cannot disappear after a repair.

### Character envelope
Dynamic, Vibrato, Bow, Desk and Transition properties have section-specific tolerances around D.

## Candidate search

The search is deliberately bounded:
- local winner;
- one near-scoring alternative;
- D Original when safe.

A candidate must pass both v5.2 Global Coherence and v5.3 Conductor Intent.

A tiny character prior is applied only among already near-scoring candidates.

## Audio authority

The Conductor layer does not listen to audio and is not the final sonic authority.

After selective convergence:
- merged full render;
- D Original full render;
- each judged against its own MIDI.

If the merged whole-song result loses too much Overall or Safety, full A/B/C/D fallback is triggered.
