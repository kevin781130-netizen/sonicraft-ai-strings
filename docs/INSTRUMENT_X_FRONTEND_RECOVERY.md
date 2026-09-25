# Instrument X inspection and SONICRAFT frontend integration

## Status

This change is a **partial behavioral reconstruction**, not recovered Instrument X
frontend source and not a complete recreation of its interface or acoustic engine.
It extends SONICRAFT's existing browser editor. The VSTGUI editor is unchanged.

The user supplied the Instrument X 1.0.1 Windows installer and requested inspection
and integration. Static unpacking produced 40 files. The exposed JavaScript files
are host utilities (`ScaleSelectedNotes`, `RemoveShortSilences`,
`SilenceSkippingPlay`), not a web frontend. Those utility scripts were inspected to
identify functionality; this work is therefore not represented as an unexposed
clean-room analysis. The implementation in `frontend/note-tools.js` is newly
written against SONICRAFT's `{id, track, start, duration, ...}` model and does not
copy the original script bodies or depend on the proprietary `SV` host API.

## Additional binary inspection

`instrument-x-pe-inventory.json` records SHA-256, PE sections and top-level resource
types for the application and five extracted plugin files (including the duplicate
ARA installation path).

- The main executable's resource types are 3 (icon), 14 (icon group), 16 (version)
  and 24 (manifest).
- Plugin resource types are 16 and 24.
- No standard dialog templates, HTML resources or string-table resources are present
  in those resource directories. Custom packed resources could still exist.
- The main executable has original `.text`/`.rdata` sections with no raw payload and
  an entry point in an unusually named section. This is evidence consistent with
  packing/protection, not identification of a specific packer.
- No separate web bundles, source maps, PDB files or original layout sources were
  found in the installation payload. Static inspection cannot establish their
  absence inside protected runtime data.
- The binaries were not executed; dynamic unpacking, layout recovery and original
  source recovery have not been completed.

The executable, plugins, models, fonts, original scripts and translation corpora
are not added to the GitHub project. Inspection metadata is included for provenance.
The previous private extraction deliverable remains the source for raw resources.

## Integrated behavior

| Feature | SONICRAFT implementation |
| --- | --- |
| Note scaling | 0.5, 0.75, 1.5 or 2 times; anchor at first scoped note or beat zero |
| Short gap closing | Extend to the next onset on the same track when the positive gap is below the threshold |
| Scope | Selected notes, current track, or project |
| Selection | Shift-click, Select Track, Clear, Ctrl/Cmd+A; group move, resize, articulation and Delete |
| History | Scaling, gap closing, group edits and Delete participate in Undo/Redo |
| Silence skipping | Merge overlapping note ranges and skip empty time with one beat of padding |
| Transport | Current-track sine preview, pause, stop, playhead, Space and Escape |
| Navigation | First visible bar, top visible pitch and playback auto-follow |
| Packaging | Include and validate the new `Frontend/note-tools.js` asset |

Short-gap behavior deliberately preserves overlapping notes and chords instead of
shortening them, which is important for SONICRAFT's polyphonic string material.
A selected scope does not bridge through an unselected intermediate note.

Preview audio is a quiet sine audition for timing/pitch, not Instrument X audio and
not neural string rendering. Compile and Auto-Loop still use the existing SONICRAFT
runtime. Tempo is constant during preview; changing tempo or editing notes stops
preview. Switching tracks and hiding the page also stops it. Project/MIDI export
continues to use the same edited note array.

## Validation

```sh
node --test frontend/tests/note-tools.test.js
python runtime/frontend_layout_gate_v70.py
python runtime/smoke_frontend_packaging_v70.py
```

For browser integration coverage, install Playwright and its Chromium browser in a
development environment, start `python frontend/editor_server.py --port 8765`, then
run `node frontend/tests/editor.browser.cjs`. Set `EDITOR_URL` for a different port.
The browser test checks actual controls, selection, saved project values,
Undo/Redo, gap closing, import, transport, navigation and responsive widths.

Local validation passed: all 7 Node tests, the existing layout/packaging/source
gates, and Playwright browser interactions using Chromium 153. The browser test
checked widths 1440, 1024, 720 and 390 pixels.

Windows acoustic rendering, VST/AAX host operation and the installer build require
Windows validation and are not covered by the browser tests.

## Remaining full-reconstruction work

The protected native frontend's layout and implementation are still unavailable.
Completing a faithful visual reconstruction requires observed screens and interaction
traces from a running installation; completing native source recovery requires a
suitable Windows reverse-engineering environment and cannot be promised from this
static extraction. This branch only claims the functionality above.
