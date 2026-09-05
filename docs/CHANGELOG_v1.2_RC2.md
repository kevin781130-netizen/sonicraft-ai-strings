# SONICRAFT AI Strings Q4 v1.2 RC2

## Final commercial packaging phase
- Three install profiles: Lite / Standard / Full HQ.
- Mode-aware signed model packs: Standard requires Compact+DAC; Full HQ adds HQ renderer.
- Profile-specific cache quota: 1 / 2 / 4 GB.
- One-command Windows finalization pipeline.
- Machine QA JSON report and actual disk-usage estimator.
- Final release manifest schema v2 with explicit profile and capabilities.
- Core installer defaults to Lite so a user never downloads multi-GB AI dependencies unless requested.

## Release rule
Public 1.2.0 must still pass Windows MSVC build, Steinberg Validator, Cubase manual QA, approved real-data model manifest, blind ABX release gate, and Authenticode signing.

## Standard Windows setup wizard update
- Added Welcome / Install Location / Options / Ready / Progress / Finish pages.
- Main application folder is user-selectable.
- VST3 folder is independently user-selectable.
- Manager and runtime now resolve the chosen install folder instead of assuming LOCALAPPDATA.
- Added optional Desktop shortcut and standard Apps & Features InstallLocation/DisplayIcon metadata.
