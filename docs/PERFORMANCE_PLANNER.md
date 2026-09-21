# SONICRAFT Symbolic Performance Planner

The Performance Planner is the optional **symbolic performance brain** in front of
the existing Strings Renderer. It does not synthesize audio and it does not replace
manual score/MIDI control.

```text
MusicXML / MIDI / editor notes
        |
        v
Symbolic frontend / written controls
        |
        v
Performance Planner (optional AI suggestions)
        |
        +---- explicit keyswitch / CC / score values always win
        v
100-Hz renderer controls
        |
        v
Strings Renderer -> VAE64 codec -> audio
```

## Why this is a separate model

`training/models/performance_planner.py` contains `SymbolicPerformancePlanner`, a
small note-sequence Transformer. It reasons across the phrase and predicts how the
notes should be performed. The existing renderer-side `PerformanceExperts` remain
local control specialists inside the audio renderer; they are not the same model.

This split keeps three concerns independent:

1. score/MIDI parsing remains deterministic software;
2. expressive interpretation can be learned and replaced independently; and
3. acoustic rendering can be trained without forcing the planner to learn waveform
   generation.

Manual mode remains valid even if no planner checkpoint is installed.

## Authority contract

The planner is advisory. `training/performance_planner_contract.py` implements the
non-negotiable merge rule:

> Any explicit written control wins over a planner prediction.

For example, if the planner suggests `spiccato / dynamics=.42` but the note carries:

```json
{
  "written_controls": {
    "articulation": "legato",
    "dynamics": 0.82,
    "legato": 1.0
  }
}
```

the renderer receives the written legato/dynamics values. The planner may still fill
controls that were not written, such as vibrato depth or bow-change probability.

The current v1 articulation vocabulary is the same 12-way vocabulary used by the
clean-room bowed-string teacher and renderer:

`sustain, legato, portamento, expressive_long, marcato, staccato, spiccato,
tremolo, pizzicato, trill, harmonic, flautando`.

The planner predicts note-level dynamics, expression, legato, bow-change
probability, transition speed/target, short-note tightness, attack character,
vibrato onset/depth/rate/jitter, and transition speed profile.

## V1 clean-room bootstrap dataset

V1 does not infer expression labels from audio. It reuses independently authored
phrase events and 100-Hz control sidecars from
`synthetic_cleanroom_bowed_v18`. Build the note-level planner dataset with:

```bash
python training/scripts/build_performance_planner_dataset.py \
  --source-index datasets/generated/cleanroom_phrases_v1/index.jsonl \
  --out datasets/processed/performance_planner_cleanroom_v1
```

Each note receives deterministic symbolic input features (pitch, duration, velocity,
tempo, metrical/phrase position, surrounding intervals, rests/gaps, and instrument)
and targets aggregated from that note's existing control-curve span.

The resulting dataset is deliberately marked:

- `training_origin=modeled`;
- `planner_supervision_kind=cleanroom_symbolic_bootstrap`; and
- `final_expression_anchor=false`.

Therefore this dataset can bootstrap phrase behavior but must not be presented as
proof of human-performance parity. A later rights-cleared human-performance corpus
can supplement or replace this bootstrap through a separately reviewed source-policy
path.

## Training

The default model is intentionally small (`d_model=128`, four Transformer layers,
four heads). It is much lighter than the audio renderer.

```bash
python training/train_performance_planner.py \
  --index datasets/processed/performance_planner_cleanroom_v1/index.jsonl \
  --epochs 80 \
  --out checkpoints/performance_planner_last.pt \
  --best-out checkpoints/performance_planner_best.pt
```

On Windows, the preferred operator entrypoint is:

```bat
TRAIN_PERFORMANCE_PLANNER.bat --index datasets\processed\performance_planner_cleanroom_v1\index.jsonl --epochs 80 --out checkpoints\performance_planner_last.pt --best-out checkpoints\performance_planner_best.pt
```

It uses the same `TRAINING_CONTROL_PANEL.bat`, `PAUSE_TRAINING.bat`, and
`RESUME_TRAINING.bat` controls as renderer training. Pause is honored at a complete
optimizer boundary and saves optimizer/scheduler/RNG/model state before exit.

## Inference and renderer handoff

Start from `training/performance_planner_input.example.json` or emit the same note
schema from the product's MIDI/MusicXML frontend. Apply the planner with:

```bash
python training/scripts/apply_performance_planner.py \
  --checkpoint checkpoints/performance_planner_best.pt \
  --input training/performance_planner_input.example.json \
  --out evidence/performance_plan.json \
  --control-curves-out evidence/performance_controls.npz
```

The JSON output records both merged controls and their authority source. The optional
NPZ is a renderer-compatible 100-Hz control sidecar. If the merged articulation is
portamento, the adapter constructs a note-transition pitch-bend curve from the
preceding note and the planned transition target.

This adapter is intentionally downstream of the authority merge: renderer controls
are generated only after written controls have overridden planner suggestions.

## Product integration boundary

The first implementation is an offline/trainable component with a stable JSON/NPZ
contract. The existing deterministic frontend can continue operating without it.
A later product integration should call the same contract after MIDI/MusicXML parsing
and before renderer control-curve construction.

The Performance Planner is **not automatically made a requirement of Release Schema
8**. Schema 8 currently governs the phrase-fine-tuned audio renderer and transition
evidence. If the planner becomes a shipping enabled-by-default model, it should gain
its own held-out symbolic/performance promotion evidence rather than silently
piggybacking on renderer promotion.
