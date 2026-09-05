# SONICRAFT v4.3 String Constraint & Transition Solver

## Objective
Use full-score lookahead to produce a more playable strings performance plan without adding another opaque realtime AI layer.

## Transition repair
Each explicit v4.1 voice lane is inspected as a sequence. For a difficult transition, all feasible string/fingering candidates are compared against the previous hand state. A change is accepted only when the alternative provides a meaningful ergonomic improvement, avoiding gratuitous fingering churn.

Risk considers:
- semitone shift distance;
- number of string crossings;
- recovery gap;
- stricter cost for connected legato transitions.

High-risk transitions are preserved but reported instead of being silently declared solved.

## Bow budget
Connected bowed phrases accumulate an estimated bow-consumption budget based on note duration and planned pressure. If a connected note would exceed the conservative instrument budget, the solver inserts a bow change and records `bow_budget_forced_change`.

This is an engineering prior, not measured centimeters of bow travel.

## Double-stop / divisi
For an exact two-note simultaneous group, v4.3 searches for a feasible stopped/open-string assignment.

A double-stop is accepted only if:
- strings are adjacent;
- stopped-finger hand-frame span is within the instrument heuristic;
- both pitches are inside configured planning range.

When accepted, the solver adopts the distinct-string fingering and shares desk/bow state across the pair. Otherwise the notes remain divisi.

Three/four-note geometries are reported separately but remain conservatively divisi. More than four independent simultaneous notes exceed the current String Voice Bus and are reported as an error.

## Constraint Report
`*.constraints.json` contains:
- issues with severity/kind/tick/source note IDs;
- simultaneous-stop groups;
- repaired transition count;
- forced bow-change count;
- unplayable/overload count;
- maximum risk.

Constraint issues are also emitted as MIDI conductor markers so a DAW user can jump to the problem area.

## Boundary
The solver does not create new samples, articulation embeddings, real string-specific timbre, or guaranteed biomechanical truth. It is a deterministic ergonomic planning layer over the existing strings system.
