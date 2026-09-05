# SONICRAFT v5.0 Local Shadow Render Auto-Loop

## Renderer authority
v5.0 talks to the existing Renderer Service over `protocol.py` TYPE_RENDER. The auto-loop never imports or invokes TorchFlowBackend / ORTFlowBackend directly.

## MIDI adapter
Compiled MIDI is reconstructed into lane-aware Shadow events. Voice channels map through the existing 4x4 String Voice bus. Keyswitch + Expression Stack are packed exactly like the Processor path. Physical CC27-35 map to opcodes 112-119, Ensemble CC36/37 to 120/121, Gesture CC38 to 122, while normal voice automation is sent as control snapshots.

## Long renders
Single service renders are limited to 45 seconds. v5.0 uses 40-second chunks by default with 0.75-second overlap. Full event history is supplied to every chunk; output master stereo is crossfaded into one WAV.

## Service lifecycle
- Reuse a ready existing service.
- Otherwise start a local service and wait for readiness.
- Only a service spawned by v5.0 is terminated by v5.0.
- Unready/failed service is a hard failure.

## Auto loop
Each round produces A/B/C/D, renders all four, judges each WAV against its own candidate MIDI, then applies the existing v4.9 Repair Policy gates. Accepted evidence may create the next round up to round 6.

## Decision artifact
Accepted final round: `*_WINNER.mid/.wav`.
Low-confidence stop: `*_REVIEW_BEST.mid/.wav`.
Every round, score, render metadata, policy before/after, stop reason and output path are stored in `*_DECISION_TRACE.json`.

## Acoustic honesty
Mock TCP rendering verifies orchestration/protocol/chunking. It does not validate the unavailable trained acoustic weights. Real model listening tests remain a release gate.
