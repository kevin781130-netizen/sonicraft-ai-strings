# v7.0 RC2 Frontend Layout Lock

**Feature freeze remains in force.** This convergence pass fixes browser-editor responsive behavior, VSTGUI clipping/bounds risks, Manager DPI/resize behavior, Product Shell Per-Monitor DPI handling, and two VSTGUI parameter-binding collisions. `FRONTEND_LAYOUT_GATE_V70.bat` is now part of the source-release contract. See `docs/FRONTEND_LAYOUT_LOCK_v7.0_RC2.md`. Real Windows/VST3/DAW/acoustic validation is still intentionally not claimed.

# SONICRAFT AI Strings Q4 v7.0 RC2 — Commercial Release Gate Ready

The performance/checkpoint core remains frozen at **v6.2** and the Instrument Editor / Stage Mixer frontend remains frozen at **v6.4**. v7.0 adds no new performance brain; it closes the Windows release process with a pinned Steinberg VST3 SDK, same-SDK official Validator evidence, hash-bound Cubase/Studio One QA, RTX/model acoustic QA, and a fail-closed final approval gate.

Windows developer order: `RC_MACHINE_PREFLIGHT_V70.bat` → `RC_BUILD_V70.bat` → `QA_CUBASE_V70.bat` → `QA_STUDIO_ONE_V70.bat` → `QA_RTX5090_ACOUSTIC_V70.bat` → `FINAL_GATE_V70.bat`. Public release additionally requires `VERIFY_AUTHENTICODE_V70.bat` + `PUBLIC_RELEASE_GATE_V70.bat`.

**Truth boundary:** this source archive does not claim that Windows/MSVC, Validator, Cubase, Studio One, RTX 5090, final trained model, or Authenticode gates have already passed. The scripts generate evidence on the real Windows machine and refuse approval when evidence is missing, skipped, stale, or tied to a different VST3 SHA-256.

See `docs/RC_GATE_V7.0.md` and `release/frontier_status_v7.0.json`.

---

# SONICRAFT AI Strings Q4 v6.4 — Instrument Editor / Stage Mixer Frontend Final Candidate

## Start here

- Normal local editor: `SONICRAFT_EDITOR_V64.bat`
- Debug editor: `DEBUG_EDITOR_V64.bat`
- Frontend integration smoke: `FRONTEND_SMOKE_V64.bat`
- Existing compile/runtime BATs are intentionally retained.

## v6.4 convergence

v6.4 freezes core feature expansion and closes the product-surface gap with a Score / Perform / Retakes / Mix workflow, editable local piano roll, MusicXML/MIDI import, expression inspector, predictive dynamics, retake/comp surface, and Master + 16-feed scoring-stage mixer. The local editor delegates compile/render to the existing v6.2 core rather than introducing a second compiler.

The VST3 source project advances plug-in state to v14 only for stage-mixer persistence. Stage Mixer is bypassed by default so the existing master path remains the default behavior.

**Release truth boundary:** this is a source/frontend final candidate. No rebuilt Windows v6.4 VST3, Steinberg Validator, Cubase, Studio One, RTX 5090 acoustic QA, final trained model QA, or bit-identical audio replay is claimed.

See `docs/FRONTEND_CONVERGENCE_V64.md` and `docs/VALIDATION_v6.4.md`.

---

# SONICRAFT AI Strings Q4 v6.2 — Acoustic Runtime Provenance / Model Environment Binding

## v6.2 Release Convergence

v6.2 keeps the v6.1 Score / Control / Policy / Evidence / Compiler checkpoint contract and extends it with an **Acoustic Runtime Binding**. It does not change the strings musical algorithms, add MIDI CC families, add ParamIDs, or change project-state schema.

Each new checkpoint additionally binds:

- model-pack manifest SHA-256 and the actual bytes of declared model weights;
- ONNX export manifest and renderer/decoder hashes when present;
- renderer implementation fingerprint;
- selected Torch / ONNX Runtime backend plus runtime/build details;
- CUDA/GPU compute capability, device identity and driver observations when available;
- OS/Python execution environment and numerical-control environment variables;
- sample rate, chunk/overlap and local-context render configuration.

The binding is path-independent: display paths stay in forensic metadata and do not enter the Checkpoint ID. A changed model, backend, framework build, renderer implementation, device/runtime capability or render configuration is reported as a structured provenance difference.

`PERFORMANCE_CHECKPOINT_V62.bat provenance CHECKPOINT.json` exports an **unsigned local in-toto Statement using the SLSA provenance predicate vocabulary** for interoperability. It is a local evidence envelope, not a claim of SLSA certification or a signed supply-chain attestation.

### Release truth boundary

v6.2 still does **not** claim bit-identical Audio Replay. Compiler/control replay remains deterministic; acoustic provenance is used to explain why a later render may differ.

This source package also does **not** claim a rebuilt v6.2 VST3, Steinberg Validator pass, real Cubase pass, real Studio One pass, or Windows real-machine Audio Replay. Those remain separate binary/host validation gates.

See `docs/ACOUSTIC_RUNTIME_PROVENANCE_V62.md` and `docs/VALIDATION_v6.2.md`.

---

## Historical v6.1 — Reproducible Performance Checkpoint / Policy–Evidence Binding

## v6.1 Project Reproducibility Layer

v6.1 remains strings-only. It adds no acoustic model, MIDI CC family, ParamID family, or project-state schema.

v6.0 made cross-song Evidence transactional and recoverable.

v6.1 adds a separate **project-local reproducibility checkpoint** so an old performance generation can be reconstructed from the actual decision environment that created it.

A checkpoint binds:

- source score SHA-256
- SONICRAFT release version
- compiler code fingerprint
- pre-round v6.0 Evidence Store commit
- five Evidence namespace hashes
- exact v4.9 Repair Policy payload / generation / profile hash
- Conductor Intent hash
- Candidate Steering Intent hash
- D / A / B / C MIDI SHA-256
- deterministic key JSON sidecar hashes
- post-round Evidence + Policy state
- result / merged MIDI bindings when available

## Input state vs output state

The important distinction is explicit.

`input_state` is the state that actually generated and ranked the current round:

- Evidence HEAD before local learning
- Repair Policy snapshot used by compiler
- Conductor Intent
- Steering Intent

`output_state` records what that round produced:

- Evidence HEAD after local evidence learning
- Repair Policy after accepted policy learning
- decision summary
- merged/final artifact hashes

Replay always targets `input_state`.

## Strict compile replay

`PERFORMANCE_CHECKPOINT_V61.bat replay ...`

Replay Verify is non-destructive.

It:

1. validates checkpoint identity;
2. validates source score SHA;
3. validates compiler code fingerprint;
4. validates the checkpoint Evidence commit and all five namespace hashes;
5. reconstructs the old Repair Policy in a temporary directory;
6. recompiles the same score with v6.1 compiler in a temporary directory;
7. compares 12 deterministic compile artifacts.

Bound compile artifacts:

- D Original MIDI
- Repair A MIDI
- Repair B MIDI
- Repair C MIDI
- score JSON
- critic JSON
- policy snapshot JSON
- conductor intent JSON
- candidate steering JSON
- archetype JSON
- archetype mixture JSON
- Judge Queue JSON

MIDI uses raw SHA-256.

JSON also receives a normalized SHA-256 that ignores machine-specific source / queue / policy paths. Musical/control values and deterministic output filenames remain part of the comparison.

### Path-independent Checkpoint ID

Checkpoint ID uses a canonical identity projection:

- source **content** SHA-256, not source filename;
- raw SHA-256 for MIDI/binary artifacts;
- normalized SHA-256 for JSON artifacts;
- Evidence commit + five namespace hashes;
- exact Repair Policy;
- compiler code fingerprint;
- Conductor / Steering intent hashes.

Raw JSON SHA-256 and byte length remain stored for forensic inspection but do not enter the Checkpoint ID.

The final regression recompiles identical state from another directory with renamed Score/Policy files and produces the **same Checkpoint ID**.

### Final result integrity

`output_state` is independently bound by `result_binding_sha256`.

Changing a finalized winner, pair-verification result, output Evidence commit, output Policy, or decision summary without updating the binding causes:

`checkpoint_result_binding_mismatch`

## No fake audio reproducibility claim

v6.1 Replay proves **compiler/control-state determinism**.

It does NOT claim bit-identical audio rendering across:
- different model weights
- different GPU/runtime versions
- different floating-point kernels
- different future renderer implementations
- different DAW hosts

No Audio or MIDI bytes are embedded in the Checkpoint.

## Explicit Restore

`PERFORMANCE_CHECKPOINT_V61.bat restore ...`

Restore is intentionally separate from Replay Verify.

Restore:
- rolls the five v6.0 legacy Evidence files back to the checkpoint input commit;
- restores the exact Repair Policy payload;
- moves Evidence Store HEAD to the requested commit;
- creates a `.pre_v61_restore.bak` backup of the current Repair Policy first.

Replay never performs this mutation.

## Evidence commit pinning

A long-term checkpoint is useless if v6.0 compaction deletes its Evidence commit.

Therefore every v6.1 Checkpoint automatically pins its input Evidence commit.

Store compaction preserves:
- recent commits
- current HEAD
- every pinned Checkpoint commit

The management command:

`PERFORMANCE_CHECKPOINT_V61.bat release CHECKPOINT.json --store STORE.json`

removes only that Checkpoint's retention pin.

After release, normal future compaction may remove the old Evidence commit.

## Separation from cross-song memory

Project Checkpoints may contain:
- score SHA-256
- artifact hashes
- exact policy payload

Those fields are intentionally **not written into the cross-song Evidence namespaces**.

v6.0 Evidence privacy/contamination rules remain unchanged.

## Release boundary

Realtime/acoustic files remain unchanged from v6.0.

No rebuilt v6.1 VST3, Steinberg Validator, real Cubase validation, real Studio One validation, or bit-identical acoustic replay is claimed in this environment.

## v6.0 Commercial Memory Foundation

v6.0 remains strings-only. It adds no acoustic model, MIDI CC family, ParamID family, or project-state schema.

The musical algorithms from v5.5-v5.9 are intentionally unchanged.

v6.0 consolidates their persistent evidence into one transaction/governance layer while preserving each algorithm as a separate namespace.

Namespaces:

1. `utility_v55`
2. `audit_v56`
3. `similarity_v57`
4. `archetype_v58`
5. `mixture_v59`

v4.9 Repair Policy remains separate because it is an active control policy, not an evidence namespace.

## Content-addressed transactions

Every namespace snapshot is:

`canonical JSON → SHA-256 → zlib → content-addressed blob`

A transaction commit records five hashes.

Unchanged namespaces reuse the same blob and do not consume another full snapshot.

The default history retains 32 commits.

## Crash consistency

The five legacy JSON files remain compatible with v5.5-v5.9 code.

At Auto-Loop startup:

1. verify all five legacy JSON files;
2. compare every canonical hash against the Unified Evidence Store HEAD;
3. if all match, continue;
4. if any namespace drifted or is invalid, preserve that payload in quarantine;
5. restore **all five namespaces** to the last complete transaction HEAD;
6. only then instantiate the legacy memory objects.

This prevents a crash between two memory writes from creating a half-old / half-new learning state.

## Commit boundary

During selective Auto-Loop:

- local Utility/Audit/Transfer/Archetype/Mixture updates execute normally;
- after the complete local decision set is finished, v6.0 captures all five namespaces as one transaction;
- the transaction is immediately verified;
- downstream Conductor / merge / whole-song verification runs only after a valid Evidence commit.

## Governance

`EVIDENCE_STORE_V60.bat` exposes:

- status
- verify
- compact
- export
- rollback

The Python manager additionally supports validated import.

### Rollback

A full rollback restores all five legacy files to one historical commit.

Per-namespace restore is supported internally for surgical recovery but does not rewrite transaction history.

### Quarantine

Invalid or transaction-drifted payloads are preserved separately instead of being silently discarded.

Quarantine cannot influence prediction or learning.

### Export / import

Evidence Store exports are path-independent and contain no machine-specific memory paths.

All referenced blobs and namespace payloads are hash/schema validated before import.

## Contamination guard

The Store rejects forbidden structural fields such as:

- audio
- MIDI
- score text
- source score
- song title
- note sequence
- filename
- intent hash
- user identity

Privacy strings may describe these exclusions, but no evidence namespace may structurally store them.

## What v6.0 does NOT do

It does not:
- merge five algorithms into one score;
- retrain the acoustic model;
- change D Original;
- change candidate ranking mathematics;
- replace Counterfactual Audit;
- absorb v4.9 Repair Policy;
- add any realtime MIDI control.

## Release boundary

Realtime/acoustic files remain unchanged from v5.9.

No rebuilt v6.0 VST3, Steinberg Validator, real Cubase host validation or real Studio One host validation is claimed in this environment.

## v5.9 Soft Cross-Song Prior

v5.9 remains strings-only and adds no acoustic model, MIDI CC family, ParamID family, or project-state schema.

v5.8 used one primary Performance Archetype. v5.9 instead represents D Original as a soft mixture of up to three nearby performance-control prototypes.

Example:

`Intimate 44.7% + Ballad 38.8% + Chamber 16.5%`

These labels remain control-envelope prototypes, not genre recognition.

## Soft classification

Mixture weights are derived from D Original aggregate controls and prototype distance.

Rules:
- maximum 3 components
- minimum retained component weight 0.08
- weights re-normalize to 1.0
- whole-profile mixture confidence must be >= 0.42
- ambiguity between two nearby prototypes is allowed; being far from the whole prototype manifold is not

## Cross-song mixture evidence

v5.9 combines discounted evidence from every active component.

Each component is weighted by:
- mixture weight
- mixture confidence
- existing v5.8 archetype trust
- new v5.9 component->context trust

The resulting cross-song prior can accelerate a cold Context to **Top-2 + D**.

It cannot unlock Top-1 + D without actual target-context evidence.

## Weighted learning

Only candidates that were actually rendered update Archetype evidence.

Evidence is distributed to mixture components proportionally to their weights.

Skipped candidates remain untouched in every component.

## Counterfactual calibration

If Counterfactual Audit discovers that a pruned candidate was materially better:
- v5.9 lowers only the mixture component->context edges used for that decision;
- higher-weight components receive a larger penalty;
- v5.8 hard-archetype trust remains unchanged;
- v5.7 Similarity Transfer edges remain unchanged;
- v5.5 exact Utility evidence remains unchanged.

## New sidecars

Compile:
`*.performance_archetype_mixture.json`

Auto-loop:
`*.archetype_mixture_memory.json`

## Downstream authority

Soft mixture is only a render-budget prior.

Actual Audio Judge, Counterfactual Audit, Global Coherence, Conductor Intent Lock, merged-vs-D full verification and full A/B/C/D fallback remain authoritative.

## Release boundary

The realtime/acoustic core is unchanged. No new training data or weights are added.

Rebuilt v5.9 VST3, Steinberg Validator, real Cubase validation and real Studio One validation are not claimed in this environment.

## v5.8 Cross-Song Control Prior

v5.8 remains strings-only. It adds no acoustic model, MIDI CC family, ParamID family, or project-state schema.

v5.7 transfers discounted Utility evidence between similar local contexts. v5.8 adds a second, weaker cross-song prior based on the D Original whole-piece performance-control envelope.

Pipeline:

`D Original → Performance Archetype → A/B/C Steering → Utility + Similarity + Archetype evidence → Render Budget → Audio Judge → Counterfactual Audit → Global Coherence → Conductor Lock → Merged-vs-D Verify`

## Performance Archetype labels

The available labels are:

- Intimate
- Ballad
- Dramatic
- Chamber
- Cinematic

These are **performance-control prototype labels**, not genre/musicological recognition.

Classification uses aggregate D-derived controls:
- Dynamic level
- Dynamic contrast
- Vibrato depth/rate
- Bow pressure
- Desk looseness
- Transition density/treatment
- Lead/Foundation role focus

Every compile writes:

`*.performance_archetype.json`

## Persistent Archetype Memory

Persistent memory is keyed by:

`Archetype + Section Character + Critic Context`

It stores only aggregate outcomes from candidates that were actually rendered:
- evidence
- Utility
- Overall
- Safety
- wins
- archetype->context audit trust

It does not store:
- audio
- MIDI
- score text
- note sequences
- filenames
- song title / identity
- intent hashes

## Cold-start behavior

A new song can borrow discounted evidence from previous songs with the same Performance Archetype.

Safety rules:
- classification confidence must be >= 0.42;
- D Original is always retained;
- pure Archetype evidence can unlock at most **Top-2 + D**;
- **Top-1 + D requires actual local target-context evidence**;
- skipped candidates never learn.

## Counterfactual calibration

v5.6 Counterfactual Audit also calibrates Archetype transfer.

If an Archetype-based prune hides a materially better candidate:
- only `archetype -> context` trust is reduced;
- v5.5 exact Utility evidence is not penalized;
- v5.7 similarity donor edges are not penalized;
- repeated failures can disable that Archetype/context edge;
- clean audits can recover the edge.

## Downstream authority remains unchanged

Archetype Memory is only a render-budget prior.

Final safety still requires:
- actual Audio Judge
- v5.6 Counterfactual Auditor
- v5.2 Global Coherence
- v5.3 Conductor Intent Lock
- full merged-vs-D Audio verification
- full A/B/C/D fallback when required

## Release boundary

The realtime/acoustic core is unchanged. No new acoustic training data or weights are added.

Rebuilt v5.8 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are not claimed in this environment.

## v5.7 Similar Experience Without a Black Box

v5.7 remains strings-only. It adds no acoustic model, MIDI CC family, ParamID family, or project-state schema.

v5.5 learned Candidate Utility only from actual renders. v5.6 audited False-Prunes. v5.7 now lets a new context borrow **discounted evidence from similar contexts** so compute savings can begin earlier without pretending the new context has local evidence it has never earned.

Flow:

`Exact Utility Memory + Similarity Transfer + Counterfactual Audit → Safe Render Budget → Audio Judge → Global Coherence → Conductor Lock → Merged-vs-D Verify`

## Hard Transfer Isolation

Transfer is allowed only when:
- Section Character is identical;
- Critic problem dimensions overlap;
- dimension Jaccard similarity is at least 0.34;
- donor local Utility evidence is sufficient;
- donor v5.6 Audit state is not disabled/high-risk;
- the target<-donor transfer edge itself is not disabled.

Cross-character transfer is forbidden. An unrelated problem type cannot lend confidence.

## Discounted Evidence

Transferred evidence is discounted twice:
1. donor evidence × context similarity × donor-audit trust × transfer-edge trust × 0.32;
2. transferred evidence has lower influence than local evidence when utility is blended.

Per-slot transferred evidence is capped at 4.0.

## No Transfer-Only Top1+D

A cold target context may use similarity transfer to reach **Top2 repairs + D**.

It may **not** reach the aggressive Top1 repair + D budget from transfer alone. Top1+D requires at least 1.5 average units of actual target-context evidence.

Therefore a new song can begin saving earlier, but cannot inherit maximum pruning confidence from another song.

## Edge-Specific False-Prune Calibration

When v5.6 Counterfactual Audit discovers that a transfer-assisted prune hid the real winner, v5.7 penalizes only:

`target context <- donor context`

The donor's own Utility Memory is unchanged.

Repeated false transfer audits can disable that edge. Clean audits can recover it. This prevents one bad analogy from destroying otherwise correct donor experience.

## New Sidecar

Each selective round writes:

`*.context_similarity_transfer.json`

It records:
- exact/local evidence;
- transferred evidence;
- donor contexts;
- similarity;
- donor Audit multiplier;
- edge trust;
- accepted/blocked donor reason;
- counterfactual transfer-edge updates.

No audio, MIDI, score text, filenames, or user identity is stored in transfer memory.

## Downstream Authority Is Unchanged

Similarity Transfer only changes how much evidence is bought before rendering. It does not decide the final performance.

The following remain mandatory downstream authorities:
- actual Audio Judge;
- v5.6 Counterfactual Auditor;
- v5.2 Global Coherence;
- v5.3 Conductor Intent Lock;
- full merged-vs-D Audio verification;
- full A/B/C/D fallback when required.

## Release Boundary

The realtime/acoustic core remains unchanged. No new acoustic training data or weights are added. Rebuilt v5.7 VST3, Steinberg Validator, Cubase host validation and Studio One host validation are not claimed in this environment.

## v5.6 Long-Term Safety for Zero-Render

v5.6 remains strings-only. It adds no acoustic model, MIDI CC family, ParamID family, or project-state schema.

v5.5 can skip low-value candidates before Shadow Render. v5.6 adds the missing long-term safety layer: it periodically renders candidates that would otherwise remain pruned, measures whether the prune would have changed the real Audio Judge winner, and self-calibrates how much each context is allowed to trust Zero-Render.

Flow:

`Utility Predictor → prune opportunity → deterministic counterfactual audit → False-Prune Rate → confidence calibration / per-context disable → Audio Judge → Global Coherence → Conductor Lock → Merged-vs-D Verify`

## What counts as a False Prune

A scheduled audit first records the hypothetical v5.5 decision. It then renders every otherwise-pruned candidate and recomputes the full A/B/C/D ranking.

A False Prune is recorded only when:
- the full-evidence winner came from the pruned set;
- it beats the hypothetical accepted winner by at least 0.025 Overall;
- winner Safety >= 0.35;
- winner Overall >= 0.35.

Small positive gains below 0.025 are tracked as near-misses but do not count as False Prunes.

## Adaptive Audit Frequency

Stable contexts:
- audit every 12 prune opportunities.

Elevated recent False-Prune Rate:
- audit every 6 opportunities.

High-risk recent False-Prune Rate:
- audit every 4 opportunities.

Disabled context:
- audit/calibrate every prune opportunity until recovery.

The schedule is deterministic. It does not depend on random sampling.

## Per-Context Zero-Render Disable

Repeated False Prunes can disable predictor pruning only for the affected context.

Trigger:
- at least 4 recent audits and False-Prune Rate >= 25%, or
- 2 False Prunes in the most recent 4 audits.

When disabled:
- predictor Zero-Render is suspended;
- the system falls back to the v5.4 Section Character primary budget;
- full counterfactual calibration continues.

Recovery requires four consecutive clean audits.

## Confidence Calibration

The auditor also scales predictor confidence according to recent audit history. A context can therefore degrade gradually from Top1+D to Top2+D or the v5.4 budget before a hard disable is necessary.

This changes compute scheduling only. It does not change notes, candidate controls, Repair Policy, Conductor Intent, or the acoustic renderer.

## Privacy / Memory

The audit memory stores only aggregate context statistics:
- prune opportunities;
- audit count;
- False Prune count;
- recent boolean audit outcomes;
- counterfactual gain aggregates;
- disabled / recovery state.

It stores no audio, MIDI, score text, filenames, or identity.

## New Sidecar

Every selective round writes:

`*.counterfactual_audit.json`

It records audit plans, actual audit events, memory generation, thresholds, and privacy boundary.

## Downstream Authority Remains

v5.6 does not replace:
- v5.5 actual-render-only Utility Memory;
- Objective Audio Judge;
- v5.2 Global Coherence;
- v5.3 Conductor Intent Lock;
- full merged-vs-D Audio verification;
- full A/B/C/D fallback.

## Release Boundary

The realtime/acoustic core is intentionally unchanged. v5.6 is a render-scheduling calibration layer only.

No new acoustic training data or weights are added. Rebuilt v5.6 VST3, Steinberg Validator, Cubase host validation and Studio One host validation are not claimed in this environment.

## v5.5 Render-Before-You-Need-It Reduction

v5.5 remains strings-only and adds no acoustic model, MIDI CC, ParamID or project-state schema.

Flow:

`Critic + Section Character + Repair Policy + actual Audio history → Utility Predictor → minimum safe local render set → Audio Judge → automatic escalation if uncertain/disagreeing → v5.2/v5.3 downstream guards`

The predictor is explainable and deliberately small. It stores only aggregate per-context Audio Judge statistics. It stores no audio, MIDI, score text, filenames or identity.

### High-confidence mode
With sufficient actual-render evidence, the first pass may render only the predicted best repair plus D Original. D is always rendered.

### Safety escalation
Every pruned candidate is restored before acceptance when:
- Audio margin < 0.025;
- the actual Audio winner disagrees with the predictor at medium/high confidence;
- winner Safety < 0.35;
- winner Overall < 0.35.

Skipped candidates never update Utility Memory. Only real rendered/Judged slots may learn.

### Context
History is bucketed by Section Character plus localized Critic dimensions. Static priors also use post-steer structural scores and the bounded Repair Policy.

### Downstream authority
The predictor is only a compute scheduler. Objective Audio Judge, Global Coherence, Long-Form Conductor Lock and full merged-vs-D verification remain authoritative.

## v5.4 Intent Before Render

v5.4 remains strings-only. It adds no acoustic model, MIDI CC family, ParamID family, or project-state schema.

v5.3 used Conductor Intent after A/B/C were generated. v5.4 moves that intent upstream: candidate control envelopes are gently steered by macro Section Character before Shadow Render.

Flow:

`D Original → Conductor Intent → A/B/C Repair → Section-Steered A/B/C → Progressive Local Render Budget → Audio Judge → Global Coherence → Conductor Lock → Merged-vs-D Verify`

## D Original is Untouched

Steering is applied only to A/B/C.

The following note identity is immutable:
- part
- pitch
- note start / end
- velocity
- voice / staff
- source ID
- string voice lane
- base articulation
- expression stack

v5.4 modifies only existing performance-control metadata such as Dynamics, Vibrato, Bow Pressure, Transition treatment and deterministic Ensemble offset.

## Section-Steered Candidate Search

### Intro
A and B are centered toward restrained dynamics/vibrato/bow energy. C remains available as deferred evidence.

### Build
A/B/C all render by default. C can push forward, but remains bounded by the D-derived Section ceiling.

### Sustain
All A/B/C remain active; Balanced is centered closest to the stable section target.

### Climax
B/C/D render first. A is deferred because an over-conservative first pass is usually low value at the intended climax.

### Release / Resolution
A/B/D render first. C is deferred to avoid wasting local render budget on an unnecessarily aggressive interpretation.

## Progressive Candidate Budget

Primary local slots:
- Intro: A/B/D
- Build: A/B/C/D
- Sustain: A/B/C/D
- Climax: B/C/D
- Release: A/B/D
- Resolution: A/B/D

If the initial Audio Judge margin is below 0.025, every deferred candidate for that window is rendered before any full-song fallback occurs.

This is a compute optimization, not a pruning of musical possibilities.

## New Sidecar

Every compile writes:

`*.candidate_steering.json`

It records:
- Intent hash
- Section Character
- slot
- note/anchor count
- Dynamic/Vibrato/Bow before and after steering
- Dynamic ceiling clamps
- structural critic score before/after steering
- active/deferred render policy

## Downstream Safety Remains

v5.4 does not replace:
- Objective Audio Judge
- v5.2 Global Coherence
- v5.3 Conductor Intent Lock
- full merged-vs-D Audio verification
- full A/B/C/D fallback

## Release Boundary

The realtime/acoustic core remains unchanged. v5.4 is candidate-generation and render-budget orchestration only.

No new acoustic training data/weights are added. Rebuilt v5.4 VST3, Steinberg Validator, Cubase host validation and Studio One host validation are not claimed in this environment.

## v5.3 Macro Performance Layer

v5.3 remains strings-only. It adds no acoustic model, MIDI CC family, ParamID family, or project-state schema.

v5.2 protected whole-piece coherence after local repair. v5.3 adds an explicit long-form conductor layer that extracts the intended macro trajectory from D Original and then locks selective repairs to that trajectory.

Pipeline:

`Score → Conductor Intent → Selective Local A/B/C/D → Audio Judge → Global Coherence → Section Character Lock → Selective Merge → Full Merged-vs-D Verify`

## Conductor Intent

Every compile writes:

`*.conductor_intent.json`

The plan is deterministic and derived from D Original only, so Repair Policy changes do not move the goalposts across R1/R2/R3.

The plan contains:
- macro section boundaries;
- Section Character: Intro / Build / Sustain / Climax / Release / Resolution;
- intended climax section and normalized position;
- Dynamic mean / peak / ceiling;
- Vibrato depth palette and rate target;
- Bow pressure and reserve floor;
- Desk looseness;
- Transition density and treatment;
- Lead / Inner / Foundation role distribution per string part.

## Section Character Lock

A local Audio winner can be rejected even when v5.2 Global Coherence passes.

Examples:
- a build section becomes louder than the intended climax;
- a release reverses into a new crescendo;
- a pre-climax repair shifts the macro climax earlier;
- a section's lead/foundation role lock is lost;
- Vibrato/Bow character drifts outside the intended section envelope.

Passing thresholds:
- Conductor Intent score >= 84
- Maximum normalized section excess <= 1.55
- zero hard Section Character violations

## Near-Scoring Conductor Substitution

The search keeps:
- Local Audio winner
- one near-scoring alternative
- D Original when safe

Candidate Audio drop limit remains 0.075.

A very small Section Character prior can break near-ties:
- Climax / Build slightly favor expressive candidates when still inside the intent envelope.
- Intro / Release / Resolution slightly favor conservative/original behavior.
- Sustain slightly favors Balanced.

The prior is intentionally tiny and cannot rescue a candidate outside the Audio drop gate.

## Stable Intent Hash

`conductor_intent.json` carries a deterministic 24-character SHA-256-derived intent hash.

Changing Repair Policy without changing the score leaves:
- section boundaries
- climax location
- section characters
- intent hash

unchanged.

## Final Audio Gate

The v5.2 full merged-vs-D whole-song verification remains mandatory:
- Merged Overall >= D - 0.025
- Merged Safety >= D - 0.04

Failure still triggers full A/B/C/D fallback.

## Release Boundary

The realtime/acoustic core is intentionally unchanged. v5.3 is a score/performance graph + orchestration layer.

No new acoustic training data or weights are added. Rebuilt v5.3 VST3, Steinberg Validator, Cubase host validation and Studio One host validation are not claimed in this environment.

## v5.2 Whole-Piece Protection After Selective Repair

v5.2 remains strings-only. It adds no acoustic model, MIDI CC family, ParamID family, or project-state schema.

v5.1 made local Phrase repair efficient. v5.2 prevents those local winners from destroying the identity of the whole performance.

Flow:

`Score → Selective Phrase Search → Local A/B/C/D Shadow Render → Local Audio Judge → Global Coherence Guard → Selective MIDI Merge → Full Merged-vs-D Verify`

## Global Coherence Dimensions

The guard compares the selectively merged Score Graph against D Original and penalizes only **new** phrase-to-phrase discontinuities beyond the original trajectory:

- Dynamic trajectory
- Vibrato character (depth + rate)
- Bow energy (pressure + reserve)
- Desk looseness / ensemble attack spread
- Transition density / treatment
- Section role distribution (lead / inner / foundation)

The original score is not forced to be flat. If D already contains a dramatic transition, v5.2 does not treat that written/performance contrast as an error.

## Near-Scoring Candidate Substitution

If a local Audio Judge winner would create a global discontinuity, v5.2 searches:

- the local winner,
- one near-scoring runner-up,
- D Original.

A replacement is allowed only when it remains inside the Audio drop limit (0.075), passes Safety/Overall floors, and restores Global Coherence.

If no coherent combination exists, v5.2 falls back to full-song A/B/C/D rather than committing an incoherent local merge.

## Full Merged-vs-D Pair Verification

After selective convergence, v5.2 renders two whole-song files:

1. Selective merged result
2. D Original

Each is Audio-Judged against its own MIDI.

The merged result is accepted only when:
- Overall >= D Overall - 0.025
- Safety >= D Safety - 0.04

If this pair gate fails, v5.2 runs the full A/B/C/D fallback.

This adds one extra whole-song verification render compared with v5.1, but protects against the case where every local window wins while the entire performance sounds structurally worse.

## Outputs

In addition to v5.1 outputs, each selective round writes:

`*.global_coherence.json`

The decision trace records:
- local Audio winner
- coherence-selected winner
- any coherence override
- whole-piece Coherence score
- maximum edge excess
- merged-vs-D full Audio comparison
- fallback reason when triggered

## Release Boundary

The realtime/acoustic core is intentionally unchanged from v5.1. v5.2 is a graph/orchestration guard.

No Steinberg VST3 SDK or target DAW host validation is available in this environment, so rebuilt v5.2 VST3, Steinberg Validator, Cubase host validation, and Studio One host validation are not claimed.

## v5.1 Selective Phrase Search / Local Repair Rendering

v5.1 remains strings-only. It reduces the dominant v5.0 compute cost without changing the realtime acoustic core:

`Score → Critic → problem-phrase search → local A/B/C/D Shadow render → local Audio Judge → selective MIDI merge → one final full render`

The default path no longer renders four whole songs every round.

## Problem Phrase Search

v5.1 combines:
- v4.8 Critic source locations;
- severity and critic dimension weights;
- latent bow / transition / gesture / ensemble risk;
- actual A/B/C repair edit locations.

Issues are mapped back to v4.7 phrase IDs and source-note IDs, then simultaneous/overlapping string-section problems are merged into one ensemble render window.

Selective mode is rejected when:
- no reliable localized problem exists;
- problem coverage exceeds 55% of the song;
- more than 6 disjoint problem windows are needed;
- too many Critic source IDs cannot be mapped;
- one local context window exceeds the conservative local-render duration limit.

Those cases automatically fall back to the proven v5.0 whole-song A/B/C/D path.

## Full-History Local Shadow Render

A local request does **not** receive a truncated MIDI event list.

The entire compiled-MIDI Shadow event history is sent to Renderer Service while only the context-expanded sample range is requested. This preserves:
- pre-window CC state;
- articulation / keyswitch state;
- Gesture state;
- Physical controls;
- active notes that began before the render window.

A real TCP mock-service regression compares a selective 3–5 second window against the same slice of a whole render and obtains maximum sample error **0.0**.

Default local context is 0.85 s before and after the problem phrase.

## Local Judge + Conservative Fallback

Each A/B/C/D local render is judged against that candidate's own event/control intent.

A local decision is accepted only when the existing gates pass:
- margin >= 0.025;
- Safety >= 0.35;
- Overall >= 0.35.

If **any** selected problem window is ambiguous, v5.1 abandons the selective assumption for that round and runs full-song A/B/C/D fallback instead of forcing a local winner.

## Selective MIDI Merge, Not Audio Splicing

Accepted local winners are merged into **D Original MIDI** only inside their selected phrase windows.

Boundary protection keeps:
- conductor/meta data from D;
- unselected notes and controls outside the window from D;
- a back-to-back next phrase that starts exactly on the selected phrase's end tick from D.

The local WAV files are diagnostic/audition files only.

After selective decisions converge, v5.1 performs **one full Shadow render of the merged MIDI**. Therefore the final master has no local-audio splice seam.

## Policy Learning

Local winners may update the existing bounded Repair Policy only when one A/B/C/D strategy has at least 60% of duration/margin-weighted local evidence.

Mixed local winners can still be merged correctly, but they do not force one global policy direction.

The existing stale-generation/hash protections remain active.

## Compute Accounting

Decision trace reports:
- local problem coverage;
- local context render frames;
- equivalent full-render cost;
- cost relative to one v5.0 round of four whole-song renders;
- final one-pass full merged render.

For example, a 20% localized context corresponds to about:
- 0.8 equivalent full renders for A/B/C/D local search;
- +1 final full render;
- 1.8 total vs 4 full renders in v5.0, roughly 45% of the prior one-round cost.

Actual savings depend on context and fallback frequency.

## Entry Point

`AUTO_LOOP_STRINGS_v51.bat <score>`

Manual compile:
`COMPILE_MUSICXML_STRINGS_v51.bat <score>`

## No Core Inflation

v5.1 adds:
- no new MIDI CC;
- no new ParamID family;
- no project-state field;
- no acoustic model;
- no bundled large model.

Project state remains **v13** and highest explicit ParamID base remains **740**.

See:
- `docs/SELECTIVE_PHRASE_LOCAL_REPAIR_V51.md`
- `docs/VALIDATION_v5.1.md`

**Release boundary:** selective search, MIDI merge and TCP mock-service local rendering are validated here. The trained acoustic model, rebuilt v5.1 VST3, Steinberg Validator, and real Cubase/Studio One host validation are not available in this environment.

## v5.0 Fully Local Self-Correcting Render Loop

v5.0 remains strings-only. It closes the manual gap left in v4.9 without changing the realtime acoustic core:

`Score → Critic → A/B/C/D MIDI → Local Shadow Render → Audio Judge → Repair Policy → next round → final decision artifact`

The v5.0 orchestrator really uses the existing `renderer_service.py` TCP protocol. It does not call Torch/ORT model backends directly, so model residency, backend selection, cache behavior and the VST Shadow Renderer share the same service contract.

## Automatic Service Reuse / Startup

If a ready Local Shadow Renderer service already exists on the configured host/port, v5.0 reuses it and leaves it running.

If no service exists, v5.0 starts one locally, waits for readiness, runs the loop, then terminates only the process it started itself.

Model/backend readiness failure is a hard stop; it is never converted into a fake render PASS.

## Full Compiled-MIDI → Shadow Event Reconstruction

The v5.0 adapter reconstructs the complete explicit String Voice event contract from generated MIDI:
- notes / note-offs;
- per-lane keyswitch articulation;
- Expression Stack;
- CC22/23/24/25/26 voice controls;
- CC27–35 physical-performance controls;
- CC36/37 ensemble timing;
- CC38 Gesture windows / v4.7 sentinel;
- CC39 lane-local micro-pitch.

Physical, ensemble and gesture controls are converted to the same Shadow opcodes already used by the VST processor (`112..122`).

## Long Scores >45 Seconds

Renderer Service deliberately rejects one request longer than 45 seconds. v5.0 therefore renders long material in safe chunks (default 40 s) with 0.75 s overlap and equal-power-like linear crossfade composition.

Every chunk receives the full event history. The existing control builders can therefore reconstruct notes/controls that began before the chunk boundary rather than treating each chunk like an unrelated new performance.

A >45 second regression is included and passes through the actual TCP service in mock mode.

## Automatic Stop Gates

The loop never keeps optimizing blindly. It stops on:
- Audio Judge margin < 0.025;
- Safety < 0.35;
- Overall < 0.35;
- stale Repair Policy generation/hash;
- renderer/service failure;
- round cap (maximum 6).

If confidence is insufficient, v5.0 emits **REVIEW_BEST** MIDI/WAV rather than falsely naming a final Winner.

If the final round is accepted, it emits **WINNER** MIDI/WAV.

Every round and decision is written into one `*_SONICRAFT_STRINGS_v50_DECISION_TRACE.json`.

## New Entry Point

`AUTO_LOOP_STRINGS_v50.bat <score>`

This single entry point:
1. compiles A/B/C/D;
2. starts/reuses Local Shadow Renderer;
3. renders all four candidates;
4. judges each candidate against its own MIDI;
5. applies the bounded v4.9 Repair Policy gate;
6. regenerates the next round when accepted;
7. exports Winner or Review-Best artifacts plus the complete trace.

For manual/diagnostic rendering, `shadow_render_auto_v50.py` can also render one compiled MIDI directly.

## No Core Inflation

v5.0 adds:
- no new MIDI CC;
- no new ParamID family;
- no project-state field;
- no acoustic model;
- no bundled large model.

Project state remains **v13** and the highest explicit ParamID base remains **740**.

See:
- `docs/LOCAL_SHADOW_RENDER_AUTO_LOOP_V50.md`
- `docs/VALIDATION_v5.0.md`

**Release boundary:** the source loop and renderer-service protocol are validated here, including real TCP mock-service rendering. The actual trained acoustic model is not available in this Linux validation environment, and no rebuilt v5.0 VST3 / Steinberg Validator / real Cubase or Studio One host PASS is claimed.

## v4.9 Closed-Loop Repair Policy

v4.9 remains strings-only and does not modify the acoustic renderer, VST state schema, MIDI CC vocabulary, or ParamID vocabulary.

v4.8 generated A/B/C structural repairs plus D Original. v4.9 closes the next loop:

`Score → Critic → A/B/C/D MIDI → actual renders → Audio Judge → gated Repair Policy update → next-round A/B/C/D`

The critical separation remains intact:
- Structural Critic evaluates performance-control coherence.
- Audio Judge evaluates rendered audio engineering/adherence.
- Personal Judge Memory / Favorite / Commit remains a separate user-taste layer.
- No one result is allowed to rewrite the acoustic model.

## Local Repair Policy Memory

Only five bounded numeric multipliers are learned:
- smoothing
- bow relief
- transition treatment
- ensemble tightness
- expressive apex preservation

Each remains in the safe range 0.65–1.35. The profile stores no audio, MIDI, score text, filenames, identity, or cloud data.

One result is deliberately weak evidence. A winner moves the profile only a small bounded step toward the characteristic strategy target.

## Hard Learning Gates

Policy is not updated unless:
- all four A/B/C/D renders exist;
- all four use the same sample rate;
- durations agree within 50 ms;
- Audio Judge winner margin is at least 0.025;
- winner Safety is at least 0.35;
- winner Overall is at least 0.35;
- the queue Policy generation/hash still matches the local profile.

A stale result can still be inspected, but it cannot train the current policy.

## Candidate-Specific Audio Judge

Each render is judged against **its own candidate MIDI**. This matters because A/B/C repairs may legitimately alter Dynamics Energy, onset behavior, transition timing and other authored controls. v4.9 does not judge all four against D's control intent.

## Next-Round Generation

Accepted learning regenerates the score with the updated policy and writes the next queue, up to a conservative maximum of six rounds.

If D Original repeatedly wins, the policy moves toward *less* repair. If B wins, it moves toward stronger structural cleanup. A and C have their own distinct targets.

## Entry Points

- `COMPILE_MUSICXML_STRINGS_v49.bat` — initial/standalone v4.9 A/B/C/D compile.
- `ITERATE_STRINGS_v49.bat <judge_queue.json> <render-folder>` — judge the four actual WAVs, gated-learn, and generate the next round.

The render folder may contain the exact expected WAV names from the queue, or simply `A.wav`, `B.wav`, `C.wav`, `D.wav`.

Project state remains v13. No new CC or ParamID family is added.

See:
- `docs/AUDIO_JUDGE_REPAIR_ITERATION_V49.md`
- `docs/VALIDATION_v4.9.md`

**Release boundary:** v4.9 does not autonomously drive Cubase/Studio One in this source-only environment. Four real rendered WAVs are required for the learning step. Steinberg VST3 SDK / real host validation are still not available here.

## v4.8 Self-Correcting Strings Performance Layer

v4.8 remains strings-only. It does not add a new acoustic model, MIDI CC family, ParamID family, or project-state schema.

After v4.7 has produced the phrase-level performance plan, v4.8 evaluates that authored result across six structural dimensions:

- Bow Reserve
- Transition treatment
- Vibrato continuity
- Dynamic long-line smoothness
- Gesture spike control
- Ensemble alignment

The critic is score/control-domain analysis only. It does **not** listen to audio and must never replace the existing Audio Judge.

## A/B/C Repair Fanout + D Original

One compile now emits four directly comparable MIDI performances:

- **A Conservative** — minimal smoothing; preserve topology; small bow-pressure relief.
- **B Balanced** — strongest structural cleanup; can introduce one safe re-bow split when bow reserve is critical.
- **C Expressive** — removes discontinuities but keeps a broader phrase apex.
- **D Original** — untouched v4.7 performance plan.

`*.critic.json` records the original dimension scores, issues, every repair edit, each repaired structural score, and the structural recommendation.

`*.judge_queue.json` maps A/B/C/D explicitly so all four can be rendered under identical acoustic settings and passed to the existing v3.7 Audio Judge.

The structural recommendation is **not auto-commit authority**.

## Repair Dimensions

### Bow Reserve
Low long-line bow reserve can trigger pressure relief. Balanced repair can create one low-risk re-bow split and break the corresponding continuous transition link rather than pretending the bow has infinite length.

### Transition
High physical transition risk is not erased. Repair increases continuity treatment and target duration where needed.

### Vibrato
Phrase-level vibrato-rate jumps and linked-boundary depth discontinuities are smoothed without forcing vibrato onto straight/non-vibrato material.

### Dynamics / Gesture
Dynamics Energy, Bow Pressure, Contact Point, Bow Speed and Micro-Pitch anchors are smoothed with bounded per-step movement.

### Ensemble
Excessive deterministic microtiming spread is narrowed while retaining desk/part separation.

## No New Runtime Bus

v4.8 candidates reuse all v4.1-v4.7 MIDI controls. No new CCs or ParamIDs are added, and project state remains v13.

See:
- `docs/STRING_PERFORMANCE_CRITIC_AUTO_REPAIR_V48.md`
- `docs/VALIDATION_v4.8.md`

**Release boundary:** no Steinberg VST3 SDK or target Windows/macOS DAW toolchain is available in this environment. Rebuilt v4.8 VST3, Steinberg Validator, and real Cubase/Studio One host validation are not claimed.

## v4.7 Long-Line Performance Layer

v4.7 remains strings-only and adds no new MIDI CC or ParamID family.

v4.6 connected notes into continuous trajectories. v4.7 groups those linked trajectories into phrase-level long lines and shapes the entire phrase as one performance gesture.

The long-line planner adds:
- phrase contour classification (`arch`, `rising`, `falling`, `valley`, `sustained`);
- long-line Dynamic Energy arc;
- phrase-level Bow Energy reserve;
- Vibrato Depth continuity;
- explicit Vibrato Rate target;
- phrase momentum;
- pressure/contact-point long-line shaping;
- low-bow-reserve warnings.

## Backward-Compatible Activation

v4.7 uses no new CC. At a v4.7 phrase start the compiler writes:

`CC38 = 1/127 sentinel → normal CC38 Gesture Amount`

The existing v4.6 runtime sees the sentinel as a harmless tiny non-zero Gesture update. The v4.7 runtime recognizes it and enables long-line shaping until the normal CC38 zero.

A v4.6 file has no 1/127 sentinel, so it keeps its old behavior.

## HQ Vibrato Physics

The HQ control contract now emits real non-zero:
- `vibrato_depth_cents`
- `vibrato_rate_hz`

inside v4.7 phrase windows.

Vibrato rate follows phrase momentum rather than restarting a target on every note. The current deterministic target range is approximately 4.65–5.70 Hz; this is a performance-control prior, not a claim that the acoustic model learned a new violinist vibrato model.

## Outputs

The v4.7 compiler produces:
- `.mid`
- `.score.json`
- `.constraints.json`
- `.ensemble.json`
- `.gesture.json`
- `.transition.json`
- `.phrase.json`

Project state remains v13.

See `docs/STRING_PHRASE_LONG_LINE_V47.md` and `docs/VALIDATION_v4.7.md`.

**Release boundary:** VST3 SDK / target Windows/macOS DAW toolchains are not available here; rebuilt v4.7 VST3, Validator and real Cubase/Studio One host validation are not claimed.

## v4.6 Phrase-Level Performance Trajectory

v4.6 remains strings-only and adds no new MIDI CC or ParamID family.

v4.5 made each bowed note internally continuous. v4.6 connects compatible consecutive bowed notes on the same explicit String Voice lane into one phrase-level trajectory.

Pipeline:
`Score → Physical → Constraint → Ensemble → Gesture → Transition Graph → HQ continuous path`

For written legato / slur / portamento connections, v4.6 now:
- keeps CC38 Gesture active across the note boundary instead of closing/reopening it;
- reconciles Dynamics Energy, Vibrato Depth, Bow Pressure, Contact Point and Bow Speed at the boundary;
- creates a renderer-side smooth written-pitch trajectory between consecutive MIDI pitches;
- suppresses the redundant hard onset on the linked second note;
- carries Legato and Transition intent across the link;
- fills the existing `transition_target_ms` physical-expert control;
- keeps the next note's note-progress away from an artificial hard-zero reset during the shift;
- keeps vibrato envelope continuity through the transition;
- preserves re-bow vs same-bow mechanics instead of treating every legato as identical.

A detached note, rest, pizzicato or closed CC38 window breaks the path and falls back to historical behavior.

## No New Control Bus

v4.6 deliberately reuses v4.5:
- CC38 Gesture Amount / Enable
- CC39 lane-local Micro Pitch

A v4.6 phrase is identified by one CC38 window spanning multiple note-ons. A v4.5 file closes CC38 at each note, so old gesture MIDI never enters the new cross-note path.

## Micro-Pitch Correction

Within a v4.6 multi-note gesture window, CC39 is interpreted directly as its documented ±50-cent float-pitch conditioning and the generic pitch-bend lane is re-centered, avoiding ambiguous double scaling.

Preview keeps the raw Shadow/HQ value untouched but scales its local historical ±2-semitone bend convention so ±50-cent CC39 remains approximately correct.

## Preview Continuity

For continuous gesture lanes, Preview inherits the previous same-lane voice's vibrato phase/jitter state and part of its envelope when the next note begins. This is a low-latency approximation; HQ is the authoritative continuous transition path.

## Outputs

The v4.6 score compiler produces:
- `.mid`
- `.score.json`
- `.constraints.json`
- `.ensemble.json`
- `.gesture.json`
- `.transition.json`

No acoustic/training data changed.

See:
- `docs/STRING_CONTINUOUS_TRANSITION_V46.md`
- `docs/VALIDATION_v4.6.md`

**Release boundary:** no Steinberg VST3 SDK / target DAW toolchain is available here. A rebuilt v4.6 VST3, Steinberg Validator, and real Cubase/Studio One host validation are not claimed.

# SONICRAFT AI Strings Q4 v4.5 — Continuous String Gesture Graph

## v4.5 Note-Internal Continuous Performance

v4.5 remains strings-only and attacks the main public Instrument X strings gap that remained after v4.4: continuous in-note gesture evolution rather than only note-level state.

Pipeline:

`MusicXML/MXL → Score Graph → Voice Bus → Physical → Constraint → Ensemble → Continuous Gesture Graph → editable MIDI + reports`

For bowed notes v4.5 creates seven bounded gesture anchors describing:
- Bow Speed
- Bow Pressure
- Contact Point
- Dynamics Energy
- Vibrato Evolution
- Lane-local Micro-Pitch Drift
- Portamento Trajectory
- derived Kinetic Response

Gesture profiles include expressive swell, accent decay, legato arc, tremolo energy, flautando air, portamento arc and sustain breathe. Pizzicato remains non-bowed and does not receive fake bow curves.

## Compact DAW Contract

The curve is baked into already-existing editable controls (CC22/23/24/25/31/33/34). Only two compact controls are new:
- CC38 Gesture Amount / opt-in enable
- CC39 per-lane Micro Pitch, centered at .5 and bounded to ±50 cents

CC39 is deliberately lane-local instead of standard channel Pitch Bend so overlapping notes inside one string part do not steal each other's micro-pitch state.

## HQ Interpolation

The compiler writes only seven anchors per note. When CC38 is active, HQ Torch and NumPy/ORT control builders linearly interpolate authored voice/physical anchors inside each gesture window. No CC38 means legacy step/automation behavior is unchanged.

Preview receives the same discrete MIDI anchors; real host-validated sub-anchor interpolation is not claimed without a rebuilt VST3.

Project state remains schema v13: gestures live in MIDI / Score Graph / `.gesture.json`, not hidden plugin state. Audio Judge identity includes Gesture Amount and lane-local Micro Pitch, so edits invalidate stale results.

See `docs/CONTINUOUS_STRING_GESTURE_V45.md` and `docs/VALIDATION_v4.5.md`.

**Release boundary:** no Steinberg VST3 SDK or target DAW toolchain is available in this environment. A rebuilt v4.5 VST3, Validator, Cubase and Studio One host validation are not claimed.

## v4.4 Quartet-Level Coordination

v4.4 remains strings-only. It coordinates the four string sections after v4.3 has already solved per-lane fingering, physical constraints, bow budget and stop/divisi feasibility.

Pipeline:

`MusicXML/MXL → Score Graph → 4×4 Voice Bus → Physical Plan → Constraint Solver → Ensemble Bow/Phrase Solver → editable MIDI + reports`

The ensemble layer adds:
- cross-part onset clustering;
- deterministic phrase IDs per explicit voice lane;
- compatible bow-direction synchronization across Vln I / Vln II / Viola / Cello;
- ensemble bow-change anchors at strong/phrase-start attacks;
- explicit bow-mark conflict detection with written notation preserved;
- deterministic small per-part/desk attack spread;
- phrase-end breathing;
- simple lead / inner / foundation role metadata;
- `.ensemble.json` sidecar;
- DAW conductor markers for ensemble conflicts.

## Compact Runtime Bus

Only two new MIDI controls are introduced:
- CC36 Ensemble Attack Offset: -8..+8 ms
- CC37 Phrase Breath: 0..20 ms

Everything else reuses v4.1/v4.2 expression and physical controls. This avoids another large realtime state system.

The authored MIDI note-on/off locations remain unchanged in the DAW. CC36/37 are interpreted by the SONICRAFT HQ renderer as explicit microtiming instructions. Legacy material without these controls follows the old v4.3 path exactly.

Preview cannot safely schedule sub-block latency without the real VST host scheduler, so Preview approximates CC36/37 through attack/tightness/transition shape. HQ Torch and NumPy/ORT paths execute the actual millisecond offset and are parity-tested.

## Written Notation Wins

Explicit `up-bow` / `down-bow` markings are never silently overwritten. If simultaneous parts contain incompatible forced bow marks, v4.4 emits `explicit_bow_direction_conflict`, preserves the score and marks the location in the conductor track.

## State / Judge

Project state remains schema v13. Ensemble timing is MIDI-authored rather than hidden state.

Audio Judge configuration identity includes the per-lane ensemble timing state, so changing Attack Offset or Phrase Breath invalidates stale Judge results.

See:
- `docs/STRING_ENSEMBLE_BOW_PHRASE_V44.md`
- `docs/VALIDATION_v4.4.md`

**Release boundary:** no Steinberg VST3 SDK or target Windows/macOS DAW toolchain is available in this environment. A rebuilt v4.4 VST3, Steinberg Validator, and real Cubase/Studio One host validation are not claimed.

## v4.3 Future-Aware String Solver

v4.3 remains strings-only. It does not add another realtime control family; instead it uses complete score context before rendering to solve the problems that a realtime callback cannot see safely.

Pipeline:

`MusicXML/MXL → Score Graph → 4×4 Voice Bus → Physical Plan → Constraint/Transition Solver → editable MIDI + Constraint Report`

The solver now:
- validates configured playable range per string instrument;
- repairs unnecessarily costly string/fingering transitions when a materially better feasible alternative exists;
- scores shift + string-crossing transition risk;
- tracks finite bow budget through connected legato phrases and inserts a bow change before estimated exhaustion;
- analyzes simultaneous notes for adjacent-string double-stop feasibility;
- actually consolidates a feasible two-note stop onto a shared desk/bow plan;
- keeps infeasible double-stops as divisi;
- treats 3/4-note stops conservatively as divisi even when a contiguous-string geometry exists;
- flags more than four simultaneous independently-expressed notes as exceeding the current 4×4 voice bus;
- writes ERROR/WARNING/INFO locations into the MIDI conductor track as DAW marker meta events;
- writes a separate `.constraints.json` report.

The v4.3 solver deliberately does not pretend that every geometrically possible triple/quadruple stop is a sustainable musical technique. It also does not invent missing acoustic content.

## Why no new ParamIDs

v4.3 reuses the v4.2 physical MIDI bus (CC27/28/29/30/31/33/34/35). The solver changes those authored decisions before rendering instead of creating another hidden control layer. This keeps the package smaller, leaves Cubase/Studio One MIDI editable, and keeps project state at schema v13.

## Stop / Divisi Strategy

A two-note simultaneous stop is consolidated only when:
- both pitches have feasible fingerings;
- they can occupy **adjacent strings**;
- stopped-finger span remains within the conservative hand-frame limit.

Otherwise the group remains divisi. For overloads above four independent voices, v4.3 emits a hard constraint issue rather than silently reusing a lane as though the result were independent.

See:
- `docs/STRING_CONSTRAINT_TRANSITION_V43.md`
- `docs/VALIDATION_v4.3.md`

**Release boundary:** Steinberg VST3 SDK and target Windows/macOS DAW toolchains are still unavailable here. Source/runtime/SDK-independent native validation can pass, but a rebuilt v4.3 VST3, Steinberg Validator, and real Cubase/Studio One host validation are not claimed.

## v4.2 Physical Performance Graph

v4.2 stays strings-only and adds a deterministic, inspectable physical-performance layer above the v4.1 4×4 per-note String Voice Bus.

For every score note the planner now chooses and records:
- playable string (G/D/A/E for violin, C/G/D/A for viola/cello)
- finger semitone and hand-position index
- shift distance from the previous note
- inferred open-string state
- bow direction
- bow-change decision
- bow pressure
- contact point
- portamento route
- divisi desk

The fingering path is solved per explicit voice lane with a continuity/ergonomics cost: it avoids unnecessary large shifts/string crossings, treats expressive/legato open strings conservatively, and preserves forced up-bow/down-bow markings. This is an explainable rule layer, not a claim that the acoustic model has learned real per-string timbre.

## Editable Physical MIDI Bus

The v4.2 compiler emits ordinary editable MIDI:
- CC27 String Selection
- CC28 Position (0..8)
- CC29 Bow Direction
- CC30 Bow Change
- CC31 Bow Pressure
- CC33 Contact Point
- CC34 Portamento Route
- CC35 Divisi Desk

CC32 is deliberately skipped because it is Bank Select LSB.

Open String does not consume another controller: it is derived from selected string + zero finger/position and remains explicit in `.score.json`.

## Runtime

The physical layer is opt-in. MIDI with no v4.2 Physical Bus events follows the prior v4.1 control path without a default physical reinterpretation.

For v4.2 material, Preview and HQ control paths project physical decisions only onto already-supported controls such as dynamics, vibrato, attack, transition, tightness, pitch-bend route and hidden bow-change probability. The physical layer does **not** create new trained articulation IDs or pretend that A-string and E-string acoustic timbre has been learned without data.

Audio Judge identity now hashes all v4.1 voice-lane expression values plus v4.2 physical-lane state, so changing fingering/bow/pressure/contact/portamento invalidates stale Judge results.

Project state remains schema v13 because note-level physical decisions are authored MIDI/Score Graph data rather than hidden project state.

See `docs/STRING_PHYSICAL_PERFORMANCE_V42.md` and `docs/VALIDATION_v4.2.md`.

**Release boundary:** no Steinberg VST3 SDK or target Windows/macOS DAW toolchain is available in this environment. A rebuilt v4.2 VST3, Steinberg Validator, and real Cubase/Studio One host validation are not claimed.

## v4.1 Strings-Only Deep Convergence

This branch deliberately focuses on strings rather than adding brass/woodwinds breadth.

v4.1 adds a backward-compatible **4×4 String Voice Bus**: Vln I, Vln II, Viola and Cello each receive four explicit expression lanes (16 MIDI channels total). The first lane of every part remains the historical CH1–4 Q4 layout, so old MIDI does not change. Extra lanes are only used when overlapping notes need independent expression.

Each explicit voice lane can carry:
- Base articulation (existing 12-class trained vocabulary)
- CC21 Expression Stack: Accent / Legato / Tenuto / Expressive bitmask
- CC22 lane Dynamics
- CC23 lane Vibrato
- CC24 Transition Speed
- CC25 Attack Character
- CC26 Short Tightness

MusicXML/XML/MXL is compiled through the v4.0 semantic Score & Expression Graph into Type-1 / PPQ960 editable DAW MIDI. Tempo, time signature, key signature, ties, slurs, dynamics, chords, string technical markings and unsupported-technique warnings are retained. Unsupported acoustic techniques such as col legno / sul ponticello / sul tasto are preserved as semantic warnings rather than falsely mapped to trained sounds.

The HQ renderer protocol now preserves `part + voice_lane` identity. Packed articulation keeps the trained base ID in the low nibble and the four-bit expression stack in the high nibble; the neural articulation embedding remains 0..11. Explicit lanes receive independent deterministic Retake identities and do not get clobbered by later part-global control snapshots.

**Honest limit:** v4.1 provides four independently expressed overlapping voices per string part. A fifth simultaneously overlapping independently-expressed note is still rendered with a deterministic lane reuse warning; this is not claimed as Instrument X “Infinite Scale.”

Project state remains schema v13: per-note expression lives in editable MIDI/Score Graph and does not force another VST state migration.

See:
- `docs/SCORE_EXPRESSION_GRAPH_V40.md`
- `docs/STRING_PER_NOTE_EXPRESSION_V41.md`
- `docs/VALIDATION_v4.1.md`

**Release boundary:** this environment still lacks the Steinberg VST3 SDK and target Windows/macOS DAW toolchain. Source/runtime/SDK-independent native validation is complete, but a rebuilt Cubase/Studio One-loaded v4.1 VST3 binary is not claimed.

## v3.9 Preference-Guided Auto Comp

v3.9 builds on v3.8 Judge Memory and v3.7 Audio Judge. It can scan unresolved phrases inside the host Locator, render/judge A/B/C/D sequentially, apply the local producer preference profile, and auto-commit only phrases that clear configurable Confidence, winner Margin and Safety gates. Low-confidence phrases remain unresolved for human review. Accepted phrases are committed once as a batch, so the operation remains one internal Undo step. Auto-committed choices never become preference evidence.

## v3.8 Judge Memory / Personal Taste

Favorite / Reject / manual Commit can teach a tiny local five-weight preference profile. The correction is explainable, confidence-gated and bounded; Safety cannot learn a negative preference. Profile data is local JSON and shared across projects, while project state v13 stores only Enable / Strength / Learn and Auto-Comp gate settings. v3.8 also fixes the v3.7 installer omission that could leave `audio_take_judge_v37.py` out of installed Runtime.

See `docs/PREFERENCE_AUTO_COMP_V39.md`, `docs/JUDGE_MEMORY_V38.md`, `docs/VALIDATION_v3.9.md`.

**Release boundary:** this environment still lacks the Steinberg VST3 SDK and target Windows/macOS DAW toolchain. Source/state/protocol/runtime and SDK-independent native code are validated, but a rebuilt host-loaded v3.9 VST3 binary is not claimed.

## v3.7 Audio-Aware Take Judge

v3.7 promotes Smart Comp from a deterministic variation heuristic to a two-stage system: **render first, judge second**. The renderer service can generate A/B/C/D for the current Performance Memory phrase and score the actual master stereo audio with a dependency-light NumPy DSP judge.

The Judge reports five engineering/score-adherence dimensions per take: **Overall, Dynamics Contour, Attack Consistency, Transition Smoothness, and Energy Stability**. A sixth **Safety** score participates in the winner calculation and is exposed for the winning take. Favorite/Reject review metadata is preserved: Favorite strongly dominates a DSP tie; Reject excludes a take.

The DSP Judge is deliberately **not marketed as taste AI**. It does not claim to know whether a timbre is emotionally or artistically superior. It measures reproducible rendered-audio behavior without new training data.

When the current phrase has a valid Judge result, v3.6 Smart Audition / Smart Commit and the current Smart Timeline slot prefer the audio-judged Winner. If no matching Judge result exists, the v3.6 Retake-contract heuristic remains the fallback.

Judge rendering is asynchronous in the Shadow Renderer worker, outside the realtime audio callback. A/B/C/D reuse the existing waveform cache, and the event-only rolling history was expanded to 90 seconds for pinned-phrase review. Stale results are guarded by exact phrase sample-range identity before Audition/Commit.

v3.7 also fixes a controller restore regression where transient reset code could overwrite previously restored **Follow Playhead, Recall Take, and Smart Rank Mode** values. State schema remains v12 because Judge scores are derived/ephemeral and need not be serialized.

See `docs/AUDIO_AWARE_TAKE_JUDGE_V37.md`, `docs/CHANGELOG_v3.7.md`, and `docs/VALIDATION_v3.7.md`.

**Binary boundary remains fail-closed:** the Steinberg VST3 SDK and target Windows/macOS DAW toolchains are not present in this environment. The VST3 source, UI, protocol, renderer-service Judge, and SDK-independent Shadow transport compile are validated, but a rebuilt host-loaded v3.7 VST3 binary is not claimed.

## v3.6 Smart Comp Timeline

v3.6 adds an eight-phrase timeline viewport over v3.5 Performance Memory. Every visible phrase reports its persistent Committed Take and a deterministic Smart Pick. Smart Pick is explicitly a **candidate-priority heuristic**, not an audio-quality prediction: it uses the actual A/B/C/D derived Retake nonce, the renderer's 8-bit nonce quantization, active Retake target/amount, MIDI Authority Lock, Retake dimension salts, and human Favorite/Reject metadata.

Favorite dominates ranking; Reject excludes a candidate. `FAV ONLY` bulk-commits unresolved phrases that have exactly one human Favorite. `AUTO UNRESOLVED` can fill unresolved phrases with the heuristic candidate as one undoable fixed-memory batch edit.

State schema v12 persists Smart Rank Mode. The timeline itself is derived from the existing persistent comp map, so it does not create a second source of truth.

See `docs/SMART_COMP_TIMELINE_V36.md`, `docs/CHANGELOG_v3.6.md`, and `docs/VALIDATION_v3.6.md`.

**Binary boundary remains fail-closed:** VST3 source/state/UI are implemented, but the Steinberg VST3 SDK and target Windows/macOS DAW toolchains are not present here. A rebuilt host-loaded v3.6 binary is not claimed.

## v3.5 Performance Memory

v3.5 added Follow/Prev/Next/Next Unresolved, Recall/Audition/Commit, persistent review metadata, coverage and browser cursor status. Review-only Favorite/Reject remains separate from commitment in v3.6.

## v3.4 Persistent Performance Comp

v3.4 made phrase A/B/C/D comp choices persistent and added fixed-memory Undo/Redo.

## v3.3 Phrase Take Comp

v3.3 introduced phrase-level A/B/C/D comping.

## v3.2 Live Retake Carousel

v3.2 introduced deterministic Manual/Auto-Loop A/B/C/D audition.

## v3.1 Host-Native Locator Scope

SONICRAFT v3.1 can use the VST3 host's musical locator/cycle range as a live performance region. In Cubase this enables the fast path **select range → P (Locators to Selection) → Host Scope Retake/Director**, without exporting or rewriting MIDI. Retake can be confined to the locator range; Director can apply a scoped Style/Looseness override while preserving global settings outside. Locator boundaries are scheduled inside the audio block alongside MIDI/automation.

This pass intentionally leaves the v3.0 MIDI Command Lane (CC102–119) intact and does not consume MIDI CC120–127. New Host Scope controls are normal VST automation parameters. See `docs/HOST_NATIVE_LOCATOR_SCOPE_V31.md`, `docs/CHANGELOG_v3.1.md`, and `docs/VALIDATION_v3.1.md`.

**Binary boundary remains fail-closed:** the v3.1 VST3 source is implemented, but this Linux environment does not contain the Steinberg VST3 SDK / target Windows or macOS toolchain, so bundled historical executables are not v3.1 binaries.


## v3.0 Host Intelligence / Project Bridge

SONICRAFT v3.0 turns the existing Performance Commander into a DAW-native command system. The v3 compiler embeds a standard-MIDI Performance Command Lane (CC102–119) that drives AI Assist, style, Smart Dynamics/Articulation, seven-dimensional Retake, MIDI Authority Lock, Phrase Director, Ensemble Looseness, Auto Divisi, stage, polyphony, AI Mix and Look Ahead. `PROJECT_BRIDGE_RETAKE.bat` and `PROJECT_BRIDGE_DIRECTOR.bat` can patch only a selected beat range and restore the previous command state at the end without rewriting notes, keyswitches or normal authored CC automation.

The same pass also repairs a backend drift found during validation: Torch/CUDA now applies the same Phrase Director, Ensemble Looseness and Retake control contract as NumPy/ORT. See `docs/HOST_INTELLIGENCE_BRIDGE_V30.md`, `docs/CHANGELOG_v3.0.md`, and `docs/VALIDATION_v3.0.md`.

**Important binary boundary:** the source/runtime bridge is v3.0, but bundled historical Windows `.exe` files were not rebuilt in this Linux validation environment. Rebuild the VST3/Product Shell on the target Windows toolchain before calling a binary v3.0 release.

## v2.9 DAW-Native Performance Compiler

Drag a normal `.mid` file onto `COMPILE_MIDI_TO_Q4.bat` to generate an editable four-track Q4 MIDI plus a `.performance.json` sidecar. Smart Divisi, phrase-level CC1/CC3 and conservative C0–B0 articulation suggestions are ordinary MIDI data, so Cubase/Studio One remains the source-of-truth editor. No cloud, no model download, no training data required for this step.


## v2.8 Performance Commander

v2.8 upgrades performance control without changing the acoustic model: real Smart Divisi for single-source quartet writing, seven-dimensional targeted Retake, MIDI Authority Lock, Phrase Director, Ensemble Looseness, Python/native policy parity, and a 34-channel stage contract (Master + 16 stereo virtual-geometry aux feeds). Legacy 24-channel responses remain accepted for backward compatibility. The five added stage feeds are virtual geometry controls, not claims of newly recorded microphone positions. See `docs/CHANGELOG_v2.8.md`.

## v2.6 In-Process Neural Engine

v2.6 keeps the acoustically promoted neural core unchanged and moves the consumer inference graph into native C++. The new path covers timeline events, independent polyphony, 33-d controls, quartet/phrase context, few-step flow sampling, decoder output, and the 11-feed/24-channel scoring stage without requiring Python or localhost IPC. Native ONNX Runtime selection is fail-closed: production checkpoints must pass six-scenario control/tensor parity, runtime ABX, existing native/low-latency promotion, and a SHA-256 artifact-bound promotion lock. Until then the existing renderer service remains the trusted fallback.

## v2.5 Ultra-Low-Latency Engine

v2.5 leaves the acoustically promoted neural core unchanged and attacks realtime response only. The Windows Product Shell now has an IAudioClient3 shared-mode event-driven WASAPI path, driver-timestamped WinMM MIDI alignment, adaptive 40/80/160 ms neural windows, sustain-correct deferred note-off semantics, and a sub-millisecond boundary dezipper. The legacy waveOut path remains as a fallback. Formal ultra-low-latency promotion is fail-closed: Windows + production ORT/Torch backend + measured WASAPI stream latency are required; MOCK evidence is rejected.

The service-free ORT path advances one step with a Python/Torch-free candidate bundle audit and a direct `OrtGetApiBase` loader probe. It is deliberately **not** promoted as the default renderer until the full C++ control builder + renderer/decoder path passes the same numerical/audio ABX gates as the existing native-runtime promotion.

**Release architecture:** prebuilt VST3 + normal Inno Setup installer. Customer machines never compile the plug-in.


## v2.4 Realtime Product Shell

The neural core is unchanged. v2.4 adds a rolling-window standalone performance shell: native Windows MIDI/audio I/O, an 11-feed scoring-stage mixer, Director/Retake controls, and fail-closed AUTO runtime selection. Smart Dynamics and Smart Articulation remain OFF by default. AUTO may select promoted ORT only when native-runtime promotion evidence and bound artifact hashes still verify; otherwise it stays on Torch.

`SonicraftAIStringsRealtimeSim` is a cross-platform engineering harness for the exact rolling-window protocol. `SonicraftAIStringsProductShell.exe` is the Windows product shell target. Final realtime promotion requires a production Windows benchmark and a hash-bound shell bundle; mock timing is never valid commercial evidence.

## v2.3 Native Production Pass

v2.3 finishes the v2.2 platform split without changing the acoustically promoted neural core. It adds a VST3-independent C++ Standalone Render Host, a rights-confirmed room-capture pipeline (log sweep -> measured 11-feed IRs -> directional profile), and a stricter no-PyTorch deployment contract that binds bundle bytes, numerical parity, runtime transparency ABX, production-hardware render RTF and the existing acoustic promotion before a reduced ONNX Runtime bundle may replace Torch. CMake can now build the standalone executable with `SONICRAFT_BUILD_VST3=OFF`, so the desktop/app boundary no longer depends on Steinberg's SDK. The embedded-ORT staging path is offline/deterministic and adds no consumer neural parameters. See `docs/NATIVE_PRODUCTION_V23.md`, `docs/ROOM_CAPTURE_V23.md`, `docs/CHANGELOG_v2.3.md`, and `docs/VALIDATION_v2.3.md`.

## v2.2 Platform Kill Gap

v2.2 closes three product/platform gaps without changing the acoustically promoted neural core: the VST declares a stereo Master plus eleven stereo auxiliary output buses, the localhost renderer can return either legacy 2-channel audio or a 24-channel Master+11-feed bundle, and SONICRAFT can build a directional scoring-room profile from user/SONICRAFT-owned or explicitly licensed IR measurements. A pure-NumPy control/stage path and opt-in ONNX Runtime backend remove the architectural dependency on PyTorch; reduced-operator ORT build scripts and a fail-closed native-runtime promotion contract require <=160 MiB staged footprint, per-file SHA-256 binding, Torch↔ORT numerical parity, an adequately powered runtime transparency ABX, and the original Schema-7 Acoustic Promotion before ORT may become a production default. The normal Torch path remains default until those real trained-artifact gates pass. Consumer neural parameters remain 3,887,433 (~7.41 MiB raw FP16). See `docs/PLATFORM_KILL_GAP_V22.md`, `docs/NATIVE_RUNTIME_V22.md`, `docs/CHANGELOG_v2.2.md`, and `docs/VALIDATION_v2.2.md`.


## v2.1 Instrument-X Clean-Room Parity

v2.1 uses Instrument X only as a **public-behavior benchmark** and closes the highest-value product gaps without importing competitor code, weights, presets, binaries, rendered training material or private room measurements. The runtime adds an opt-in Performance Director (predictive dynamics + smart articulation), deterministic targeted performance Retakes, up to 16 independent overlapping voice lanes per string part, an internally phase-coherent 11-feed virtual scoring stage with four macro perspectives, a dependency-free MusicXML converter, and functional CPU fallback. Strict MIDI Authority remains stronger than the benchmark: Smart Dynamics/Articulation default OFF, Manual remains authored, and Retake never rewrites written note pitch or explicit pitch-bend. The acoustically promoted Schema-7 v2.0 model pack remains compatible and the consumer neural core remains 3,887,433 parameters (~7.41 MiB raw FP16). See `docs/INSTRUMENT_X_CLEAN_ROOM_V21.md`, `docs/CHANGELOG_v2.1.md`, and `docs/VALIDATION_v2.1.md`.

## v2.0 Acoustic Promotion

v2.0 freezes the consumer neural architecture and turns acoustic quality into a winner-take-all promotion contract. Rights-cleared REAL80/MODEL20 material is forged and deterministically segmented for codec evaluation; codecs are compared with string-specific stereo, phase-derivative, harmonic-texture, transient and spectral metrics; codec transparency and generated-vs-real listening are scored independently with listener-level QA and statistical guards. Candidate checkpoints cannot ship. Only after both blind gates pass does a post-ABX Promotion Seal bind the winning codec/evidence SHA-256 into HQ, Frontier and decoder checkpoints without changing model tensors. Schema 7 then fail-closes on any evidence, winner or checkpoint mismatch. Consumer neural parameters remain unchanged at 3,887,433 total (~7.41 MiB raw FP16). See `docs/ACOUSTIC_PROMOTION_V20.md`, `docs/SOURCE_SCOUT_V20.md`, `docs/CHANGELOG_v2.0.md`, and `docs/VALIDATION_v2.0.md`.

## v1.9 Sound Forge

v1.9 stops spending the complexity budget on generic backbones and attacks the acoustic bottleneck directly: every audio item can be rights-gated, hashed, de-duplicated and quality-graded before training; Forge quality only redistributes probability inside the immutable REAL80/MODEL20 lanes; modeled clean-room examples gain a zero-runtime-parameter latent/physics geometry constraint; codecs compete on the same held-out real-string clips with quality-first / size-second ranking; schema 6 requires Sound Forge, codec tournament and codec ABX evidence in addition to generated-vs-real ABX. Consumer neural parameter count remains the v1.8 Frontier Core (~7.41 MiB raw FP16 renderer+decoder). See `docs/SOUND_FORGE_V19.md`, `docs/CODEC_TOURNAMENT_V19.md`, `docs/SOURCE_SCOUT_V19.md`, `docs/CHANGELOG_v1.9.md`, and `docs/VALIDATION_v1.9.md`.

## v1.8 Frontier Sound Core

v1.8 moves the main innovation budget from generic open-source backbone hunting to string-specific sound and ensemble intelligence. Acoustic training is fail-closed at **80% rights-cleared real strings / 20% independently modeled bowed-string physics**. Real recordings remain the only final-timbre/adversarial-real authority; modeled data supplies exact scarce physics and section-dispersion supervision. The Frontier Context Adapter adds only 5,160 parameters, keeping the current shared renderer + VAE64 decoder at about 7.41 MiB raw FP16 weights. Schema 5 prevents future releases from silently drifting away from the 80/20 contract. See `docs/STRING_TRAINING_FRONTIER_V18.md`, `docs/CLEAN_ROOM_SWAM_V18.md`, `docs/CODEC_ABX_V18.md`, and `docs/VALIDATION_v1.8.md`.

See `docs/PREBUILT_COMMERCIAL_RELEASE_v1.3_RC3.md`.


## v1.7 Open-Source Frontier Exit

v1.7 exhausts the remaining high-leverage permissive generic path with step-conditioned Shortcut training while keeping a single shipping renderer, compresses the safe frontier renderer to 2.60M parameters through Shared-AdaLN + joint expert fusion, fixes CC3 authority, and adds SONICRAFT-owned zero-weight quartet hidden physics plus persistent tile-level incremental DAW caching. An aggressive 1.12M tied-weight challenger remains ABX-gated. See `docs/MIT_ACCELERATION_V17.md`, `docs/SOURCE_SCOUT_V17.md`, and `docs/VALIDATION_v1.7.md`.

## v1.2 RC2 commercial release gate

Public release is fail-closed. Run `installer/BUILD_COMMERCIAL_RELEASE.ps1` on the target Windows build machine after final rights-cleared weights and blind release metrics are ready. See `docs/VALIDATION_v1.1_RC1.md`. The core installer stays small; the verified acoustic Model Pack is built separately.

# SONICRAFT AI Strings Q4 v1.2 RC2

**Commercial Release Candidate.** The release path is now fail-closed for model provenance, checkpoint hashes, VST3 validation, held-out quality metrics and public code signing.

# SONICRAFT AI Strings Q4 v1.2 RC2

Local AI string-renderer VST3 project for **Violin I / Violin II / Viola / Cello**, designed around an orchestral MIDI workflow rather than a prompt-driven music generator.

## v1.2 RC2 release / Shadow Render knife

v1.2 RC2 turns the training prototype into a Windows release-shaped product:

- real `SONICRAFT_AI_Strings_Setup.exe` x64 Windows bootstrapper;
- real `SONICRAFT_AI_Strings_Manager.exe` x64 Windows manager bootstrapper;
- VSTGUI editor embedded into the VST3 project;
- actual VST worker -> localhost Shadow Renderer Service -> phrase cache -> VST crossfade path;
- one shared CUDA service for multiple VST instances, so models are not duplicated per track;
- one-click Windows Release build + per-user VST3 installation pipeline;
- Start Menu manager, repair/uninstall registration, model folder management;
- Cubase-oriented 12-articulation / CC workflow kept intact;
- heavy models and datasets remain external.

### Core MIDI map

- **CC1 = Dynamics / bow intensity / timbre** — never treated as a simple volume fader.
- **CC3 = Vibrato depth** — Straight / Light / Natural / Deep / Intense anchors with continuous interpolation.
- **CC11 = Expression / phrase gain**.
- **CC20 = AI speed intent** — Auto / Slow / Normal / Fast.
- CC7 Volume, CC10 Pan, CC64 Hold, CC68 Legato Override, CC91 Room, Pitch Bend expressive pitch.

Articulations remain exactly 12: Sustain / Legato / Portamento / Expressive Long / Marcato / Staccato / Spiccato / Tremolo / Pizzicato / Trill / Harmonic / Flautando on C0-B0.

## Front end

`resource/SONICRAFT_AI_Strings_Q4.uidesc` provides the in-plugin VSTGUI front end. It exposes musical controls only: mode, section, CC1/3/11, articulation, speed intent, transition, attack, tightness, room, humanize, AI mix and look-ahead. It avoids exposing neural-model internals to the composer.

## Windows install

Double-click:

`SONICRAFT_AI_Strings_Setup.exe`

The preferred install path is the official per-user VST3 location:

`%LOCALAPPDATA%\Programs\Common\VST3\SONICRAFT AI Strings Q4.vst3`

The setup installs the Manager even when a binary repair is needed. If no prebuilt VST3 bundle is present, it calls the Windows build pipeline automatically.

### Binary-build requirement

The official Steinberg Windows VST3 SDK target uses **MSVC 2022**. This portable package therefore does not pretend that a Linux-built file is a usable Cubase DLL. On the target Windows machine, Setup / `scripts\BUILD_VST3.bat`:

1. detects Visual Studio 2022 / Build Tools C++;
2. downloads the official Steinberg VST3 SDK recursively if needed;
3. builds x64 Release with VSTGUI;
4. stages `release\SONICRAFT AI Strings Q4.vst3`;
5. installs it to the per-user VST3 directory.

No placeholder `.vst3` and no synthetic smoke model is labelled as a production binary.

## AI renderer state

LIVE remains the immediate low-latency preview. AUTO/HQ now have a real asynchronous runtime route: the VST audio callback pushes fixed events into a lock-free ring; a worker sends rolling phrase snapshots to `127.0.0.1:49337`; the shared CUDA service renders Compact/HQ + DAC audio; completed phrases enter a bounded cache and are crossfaded into playback. No CUDA/socket/file work runs in the audio callback.

The musical model keeps separate Vibrato, Legato, Portamento and Bow-change experts, tempo-aware transition timing, learned CC3 physical calibration, HQ teacher + Compact distillation and fail-closed commercial data provenance. Standard VST processing does not expose arbitrary future MIDI, so Look Ahead controls rolling context/render tail/cache behavior rather than pretending to inspect future bars.

The final “difficult to distinguish from a real recording” checkpoint still requires actual rights-cleared recordings to be trained on a CUDA system. The installer/runtime work in v1.2 RC2 does not falsely convert an untrained checkpoint into a finished acoustic model.

## Main Windows entry points

```text
SONICRAFT_AI_Strings_Setup.exe
SONICRAFT_AI_Strings_Manager.exe
scripts\BUILD_VST3.bat
scripts\BUILD_AND_INSTALL_VST3.bat
scripts\CONTINUE_TRAIN_V08.bat
```

See `docs/SHADOW_RENDER_RUNTIME_v1.2 RC2.md`, `docs/WINDOWS_INSTALLER_AND_UI_v1.2 RC2.md` and `docs/VALIDATION_v1.2 RC2.md`.

## v1.4 MIT acceleration pass

This release adds a fail-closed MIT source harvester and a compact AdaLN-Zero rectified-flow DiT candidate backend. VIOLET source architecture is benchmarked without importing its restricted/unclear datasets or checkpoints; TorchCrepe can be fetched for offline high-resolution vibrato/portamento supervision. Run `scripts\\FETCH_MIT_ACCELERATORS.bat` on the development/training machine. Third-party source is not bundled in the tiny consumer core.


## v1.5 MIT acceleration pass 2

The AdaLN-Zero flow-DiT candidate is now connected to the real renderer/train path rather than existing as an isolated module. A `nano_dit` challenger cuts parameter count by 39.8% versus the legacy compact preset before quantization, while promotion remains quality-gated. Runtime adds deterministic rendering, fixed-context audio-space tiled overlap, MIDI-authority CFG hooks and Euler/Heun flow sampling without extra model weights. Reflow distillation targets a 4-step renderer, and TorchFCPE/ACE-Step native runtime techniques are development-only challengers. See `docs/MIT_ACCELERATION_V15.md`.


## v1.6 Frontier Entry / MIT exhaust pass

The last high-leverage generic path is now attacked at the codec boundary. v1.6 adds a rights-cleared-training-ready 48 kHz / 1600x / 64-d continuous strings VAE challenger, training-only spectral adversarial supervision, native PyTorch SDPA, and 64-d `frontier_dit` / `micro_dit` renderers. Shadow Render no longer hard-codes 1024 channels / 25 Hz and schema-3 model packs can ship only the selected VAE64 decoder instead of the DAC stack. The v1.5 renderer path remains backward compatible. See `docs/MIT_ACCELERATION_V16.md`, `docs/SOURCE_SCOUT_V16.md`, and `docs/VALIDATION_v1.6.md`.
