# SONICRAFT Orchestra Engine v7.1 — Public Workflow Parity Target

This document defines the product-facing target for the 15-instrument SONICRAFT orchestra engine.

The goal is public-workflow parity at the composition/DAW layer, implemented with SONICRAFT-owned code and runtime contracts. It does not claim binary compatibility with, or reproduction of, any proprietary renderer internals.

## 15-instrument model plane

The stable instrument order is:

1. Double Bass
2. Cello
3. Viola
4. Violin
5. Piccolo
6. Flute
7. Oboe
8. Clarinet in A
9. Bassoon
10. Tenor Saxophone
11. Alto Saxophone
12. French Horn
13. B-flat Trumpet
14. Tuba
15. Trombone

`kParamOrchestraInstrument` is independent from the legacy four-string selector, so older DAW automation and project state remain readable.

## Model loading path

Local proprietary model bytes remain outside Git.

`runtime/dnni_model_shell.py` validates DNNI v4 containers and registry identity.

`runtime/build_dnni_vst_catalog.py` performs heavyweight SHA-256 verification outside the plug-in and writes a local `sonicraft_dnni_catalog.txt`.

The VST3 native runtime reads this catalog through `src/dnni_model_manifest.h` and performs lightweight file-size/header/layout verification only. It never hashes multi-gigabyte catalogs or accesses model files from the audio thread.

Runtime environment overrides:

- `SONICRAFT_DNNI_CATALOG`: explicit catalog path.
- `SONICRAFT_DNNI_DIR`: directory containing `sonicraft_dnni_catalog.txt`.

## Renderer ABI

`src/orchestra_engine_contract.h` is the stable boundary between the VST3/editor and a renderer implementation.

It already represents:

- 15 instrument identities;
- polyphonic notes;
- phrase timing and tempo;
- stacked articulation flags;
- note dynamics / expression / vibrato / timbre;
- micro-pitch;
- attack and transition controls;
- dynamics, pitch and vibrato automation curves;
- retake amount / seed / target;
- 16-feed microphone mixer;
- verified DNNI model binding.

No proprietary tensor names, tensor shapes, layer topology or decoder assumptions are part of the ABI.

## Product-facing feature target

| Capability | Current contract/shell status | Acoustic renderer status |
| --- | --- | --- |
| VST3 instrument | Existing | Existing legacy preview path |
| 15-instrument selector | Implemented | Model-specific synthesis pending |
| DAW state persistence | Implemented (state v15, v3-v14 compatible) | N/A |
| MIDI input / host transport / tempo | Existing | Existing legacy preview path |
| MusicXML / MIDI editor ingestion | Existing frontend | Needs 15-instrument mapping |
| Smart articulation | Existing controls | Needs orchestra renderer mapping |
| Stacked articulations | ABI implemented | Renderer implementation pending |
| Predictive dynamics | Existing controls + curve ABI | Renderer implementation pending |
| Continuous pitch / micro-pitch | Existing lane controls + curve ABI | Renderer implementation pending |
| Vibrato curve | ABI implemented | Renderer implementation pending |
| AI/performance retakes | Existing take system | Renderer-specific variation pending |
| Independent polyphony | Existing control | 15-instrument renderer pending |
| Mic mixer | Existing 16-feed mixer | Model/room synthesis pending |
| Multi-output | Master + 16 stereo aux buses already exposed | Renderer routing pending |
| Model discovery | Implemented | N/A |
| Source/weights provenance | Implemented | N/A |
| Selected-model readiness status | Implemented | N/A |
| Multi-track editor | Existing frontend foundation | 15-instrument UX expansion pending |
| Automation follows note edits | Frontend work pending | N/A |

## Compatibility rule

Do not change `kPartCount=4` merely to add orchestra instruments. The old part ParamID ranges were designed around four string parts. Orchestra identity/model selection is a separate ABI so old project state and automation IDs are not invalidated.

## Readiness truth

At this stage the shell can locate and validate model containers and expose a complete performance/render request to a future renderer. It does **not** yet interpret the opaque DNNI weights as a runnable neural network, and therefore does not yet produce the 15 instrument timbres from those weights.
