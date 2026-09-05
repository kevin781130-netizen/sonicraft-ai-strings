# SONICRAFT AI Strings Q4 v7.0 RC2 — Frontend Layout Lock

## Scope

This pass is a release-convergence and frontend-layout lock. It does **not** add another performance engine, memory layer, policy layer, or acoustic model feature.

The goal is to prevent the recurring classes of UI failure that are especially visible in DAW plug-in hosts and Windows DPI environments: clipped text, controls extending past their parent panel, crowded segmented buttons, accidental horizontal overflow, fixed-width toolbar collapse, and visual controls that are accidentally wired to unrelated audio parameters.

## Standalone Instrument Editor

`frontend/index.html` now uses a responsive constraint system rather than a single coarse breakpoint.

- universal `box-sizing:border-box` and `min-width:0`
- flexible top bar and workspace columns using `minmax()` / `clamp()`
- wrapping toolbar controls
- flexible editor rows rather than brittle `display:contents`
- horizontal scrolling only inside surfaces that require it (articulation segments and microphone mixer)
- safe text wrapping / ellipsis
- responsive breakpoints at 1320, 1120, 930 and 720 CSS px
- compact-height behavior below 800 and 680 CSS px
- mixer no longer forces a 1080 px element outside its parent

## Native VSTGUI

The static VSTGUI layout is now source-locked to 1440×900 until actual host/DPI scaling is validated on Windows. This is deliberate: the previous file advertised a much smaller minimum size while its child coordinates remained fixed, which allowed a host to request a size that the controls could not safely fit.

Corrections include:

- all Score workflow labels moved inside their actual parent bounds
- narrow segmented controls widened or abbreviated where needed
- pseudo-multiline `CTextLabel` strings split into independent labels
- high-risk long articulation / performance / retake labels shortened without changing the underlying parameter values
- Score-page `SELECT / DRAW / HQ` controls removed from the real Engine Mode parameter
- Score-page visual `ZOOM` control removed from the real LookAhead audio parameter
- Vln I speed-profile control corrected from a misleading continuous slider to the actual Auto / Slow / Normal / Fast discrete parameter
- `Mode` is now guarded so only the actual `LIVE,AUTO,HQ` engine selector may bind that parameter

The 1440×900 lock should only be relaxed after the Windows Cubase and Studio One real-host scaling matrix has been tested.

## Manager / Product Shell

### Manager (WinForms)

- `AutoScaleMode = Dpi`
- startup size is clamped to the current Windows working area
- the form has a scroll fallback when the working area is unusually small
- main tabs anchor to all sides
- tab pages permit scroll fallback
- close/status controls are anchored safely
- compatible text rendering is enabled for generated labels/buttons

### Product Shell (Win32)

- Per-Monitor DPI Awareness V2
- DPI-aware initial window dimensions
- UI scale is clamped to the current monitor working area so 125%/150% DPI cannot force the fixed base surface beyond a small display
- `WM_DPICHANGED` handling
- DPI-scaled child control rectangles
- DPI-scaled Segoe UI font rebuild and reflow

The Win32 Product Shell source is statically checked in this package. A real Windows binary build remains part of the intentionally unclaimed machine gate.

## Frontend Layout Gate

`runtime/frontend_layout_gate_v70.py` is a fail-closed source gate. It validates:

1. responsive browser-editor contracts and banned overflow patterns;
2. duplicate HTML IDs and JavaScript syntax;
3. VSTGUI XML parsing;
4. child bounds against parent bounds;
5. approximate text width against label width;
6. segmented-button label width against segment width;
7. absence of pseudo-multiline literal `\\n` labels;
8. protection against Score editor controls reusing Engine Mode / LookAhead parameters;
9. WinForms DPI/resize contract;
10. Win32 Per-Monitor DPI contract.

`RC_SOURCE_GATE_V70` runs this layout gate automatically. A frontend regression therefore blocks source release convergence instead of becoming a visual defect discovered after packaging.

## Release boundary

Source-level frontend convergence can be marked PASS when this gate and the existing frontend/packaging/release regressions pass.

Still explicitly not claimed here:

- Windows VST3 binary rebuild
- actual VST3 rendering/scaling at 100%, 125%, 150%, 175% and 200% DPI
- Steinberg Validator
- Cubase real-host QA
- Studio One real-host QA
- Windows Product Shell binary verification
- RTX 5090 acoustic QA / final trained model QA
- bit-identical audio replay

Those remain real-machine gates and must not be inferred from this source lock.
