# SONICRAFT v6.4 Validation Record

## Executed in this package build environment

- VSTGUI UIDescription XML parse: PASS.
- Required v6.4 Score / Perform / Retakes / Mix templates: PASS.
- Required Stage Mixer ParamID/tag contract 810–828: PASS.
- Browser editor JavaScript syntax (`node --check`): PASS.
- Local editor server smoke / MusicXML export: PASS.
- Editor Project → MusicXML → existing v6.2 Score Graph integration: PASS.
- Editor Project → MusicXML → existing v6.2 Compiler integration: PASS.
- Clean CMake build with `SONICRAFT_BUILD_VST3=OFF`: PASS to 100%.
- Native v6.2 Acoustic Runtime Provenance smoke: PASS.
- Native v6.1 Performance Checkpoint smoke: PASS.
- Native v6.0 Evidence Store smoke: PASS.
- Native v4.1 string-expression/voice-bus smoke: PASS.
- Native v3.3 take-comp smoke: PASS.

## Not executed here

- Windows/MSVC v6.4 VST3 rebuild: NOT RUN.
- VSTGUI runtime visual inspection inside an actual VST3 host: NOT RUN.
- Steinberg Validator: NOT RUN.
- Cubase: NOT RUN.
- Studio One: NOT RUN.
- Windows ProductShell build: NOT RUN.
- RTX 5090 acoustic render QA: NOT RUN.
- final trained model QA: NOT RUN.

## Interpretation

The frontend and source integration are phase-complete enough to freeze feature work. The remaining gates are binary/host/acoustic validation. A failure in those gates should be fixed as a release bug; it should not automatically reopen feature expansion.
