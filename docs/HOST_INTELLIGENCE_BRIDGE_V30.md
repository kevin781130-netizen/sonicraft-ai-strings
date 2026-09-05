# SONICRAFT v3.0 — Host Intelligence / Project Bridge

v3.0 makes SONICRAFT performance intelligence addressable from ordinary MIDI rather than requiring a proprietary note editor.

## Performance Command Lane

SONICRAFT reserves MIDI CC **102–119** for global performance commands. These controller numbers are undefined/reserved in the MIDI 1.0 controller table and do not replace the conventional musical lanes already used by SONICRAFT (CC1/3/7/10/11/20/64/68/91 and Pitch Bend).

The VST3 controller maps the command lane directly to the existing SONICRAFT parameters:

| CC | Parameter |
|---:|---|
| 102 | AI Performance Assist |
| 103 | Performance Style |
| 104 | Smart Dynamics |
| 105 | Smart Articulation |
| 106 | Retake Target |
| 107 | Retake Amount |
| 108 | Retake Seed / nonce |
| 109 | MIDI Authority Lock |
| 110 | Phrase Director |
| 111 | Ensemble Looseness |
| 112 | Auto Divisi |
| 113 | Stage Perspective |
| 114 | Independent Polyphony |
| 115 | AI Mix |
| 116 | AI Look Ahead |
| 117 | Layout Mode (Single / Q4 Multi) |
| 118 | Single Section Instrument |
| 119 | Humanize |

The v3.0 compiler sets **Q4 Multi** explicitly and duplicates the tick-0 command snapshot to all four Q4 part tracks. This intentionally supports both one multi-timbral Q4 plug-in and four independently routed plug-in instances.

## Region-scoped Project Bridge

`runtime/project_bridge_v30.py` edits **only** SONICRAFT command CCs in the requested beat/tick range. It does not rewrite musical notes, articulation keyswitches, normal CC automation, tempo/meta data, or unrelated MIDI events.

A region is transactional:

1. capture the command state immediately before the region;
2. write requested commands at region start;
3. restore the captured state at region end;
4. if authored command automation already exists exactly at the end tick, it runs after the restore and therefore remains authoritative.

This makes a local Retake or Director change reversible and prevents it leaking into later cues.

### One-click helpers

- `COMPILE_MIDI_TO_Q4.bat` — v3.0 compile + host-command snapshot.
- `PROJECT_BRIDGE_RETAKE.bat` — region-scoped Retake target/amount/seed.
- `PROJECT_BRIDGE_DIRECTOR.bat` — region-scoped Assist/Style/Smart Dynamics/Smart Articulation/Phrase/Looseness.
- `PROJECT_BRIDGE_CLEAR.bat` — remove SONICRAFT command CCs from a region only.

### CLI example

```text
python runtime\project_bridge_v30.py apply My_Q4.mid --start-beat 16 --end-beat 24 --retake-target dynamics --retake-amount .7 --seed 17 --authority on
```

The output MIDI and `.bridge.json` are deterministic for identical inputs and commands. The bridge history stores SHA-256 of input/output and the effective command values after MIDI's 7-bit transport quantization.

## Backend parity repair in v3.0

During this pass the Torch/CUDA control builder was found to be behind the NumPy/ORT contract. It did not fully apply Phrase Director, Ensemble Looseness, or the newer Micro-Pitch/Timing/Bow Retake inputs. v3.0 aligns that path and adds a field-by-field Torch↔NumPy performance-control parity smoke.

## Deliberate limits

- This is a MIDI/VST3 host bridge, not ARA and not a direct Cubase/Studio One selection API.
- A DAW range is represented by exported/imported MIDI beat or tick boundaries.
- The VST3 command mapping source is implemented but cannot be binary-validated without Steinberg VST3 SDK + target Windows/macOS toolchain.
- No acoustic weights or training data are changed by v3.0.
