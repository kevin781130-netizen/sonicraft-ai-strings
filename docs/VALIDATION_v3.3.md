# SONICRAFT v3.3 Validation

PASS in this environment:
- v3.3 phrase take comp C++ smoke
- v3.3 source contract smoke
- v3.2 deterministic carousel smoke and source contract
- v3.1 host cycle scope smoke
- v3.0 Host Command Lane smoke
- v2.8 Performance Commander smoke
- clean VST-independent CMake build
- in-process engine: 34 channels

Boundary:
- Steinberg VST3 SDK / target Windows/macOS toolchain is not present here, so a rebuilt VST3 binary is NOT claimed.
- Phrase comp choices are runtime-session state in v3.3; persistent comp-map serialization is intentionally not claimed.
- No acoustic weights/training data were changed.
