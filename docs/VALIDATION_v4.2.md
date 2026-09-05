# SONICRAFT v4.2 Validation — String Physical Performance

Validated 2026-09-01 in the available Linux environment.

## v4.2 PASS
- String Physical Planner: playable string/fingering path, position, shift, open-string state.
- Bow direction/change planner including forced up-bow/down-bow behavior.
- Bow pressure, contact point, portamento route and divisi desk generation.
- MusicXML/XML/MXL -> Type-1 PPQ960 physical strings MIDI.
- Physical MIDI controllers: CC27,28,29,30,31,33,34,35; CC32 absent by design.
- Physical runtime is opt-in; no physical events returns the v4.1 control path.
- Partial physical authoring is field-presence aware: Bow Pressure alone does not imply Position=0/Open String.
- Bow Change is onset-scoped in HQ hidden bow-change probability.
- Torch / NumPy physical control parity.
- C++ physical residual smoke.
- Audio Judge identity includes per-lane v4.1 expression and v4.2 physical state.
- Installer/prebuilt module/version convergence.

## Renderer / native PASS
- v4.2 encoded physical String Voice service: 12000 frames / 34 channels.
- v4.1 encoded String Voice service regression: 12000 / 34.
- legacy renderer client.
- multi-out regression: 12000 x 34.
- v3.7 Judge protocol.
- clean VST-independent CMake build.
- native in-process engine: 9600 frames / 34 channels.
- Promotion Guard + tamper rejection.

## Backward regressions PASS
- v4.1 per-note String Voice Bus / Score Graph.
- v3.9 Preference-Guided Auto Comp.
- v3.8 Judge Memory / Preference Client.
- v3.7 Audio Judge.
- v3.6 Smart Timeline.
- v3.5 Performance Memory.
- v3.4 Persistent Comp.
- v3.3 Phrase Comp.
- v3.2 Carousel.
- v3.1 Host Scope.
- v3.0 Project Bridge / Command Lane.
- v2.9 Performance Compiler.
- v2.8 Performance Commander.
- ORT no-Torch 12000 x 34.

## Integrity
- UIDESC XML PASS.
- 116 explicit ParamID bases/IDs scanned; zero duplicate numeric assignments. Highest explicit base: 660.
- State schema remains v13.

## Honest boundary
- String/fingering selection currently shapes performance-response controls; true G/D/A/E per-string acoustic timbre is not claimed without matching acoustic/training evidence.
- Bow Pressure / Contact Point are normalized control priors, not measured physical force/bridge-distance units.
- Four independent overlapping expression voices per string part remain the v4.1 limit; infinite-scale polyphony is not claimed.
- Unsupported col legno / sul ponticello / sul tasto remain semantic warnings unless acoustic capability exists.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are absent. Rebuilt v4.2 VST3, Steinberg Validator and real Cubase/Studio One host validation are not claimed.
