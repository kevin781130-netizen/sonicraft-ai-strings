# SONICRAFT AI Strings Q4 v3.1 — Host-Native Locator Scope

- Added VST3 host-cycle/locator awareness using project-time and cycle-range ProcessContext data.
- Added Host Scope modes: Off / Locator Retake / Locator Director / Locator Both.
- Added Host Scope Style and Host Scope Looseness overrides.
- Added in-block locator boundary scheduling so scoped state changes do not wait for a later process block.
- Preserved v3.0 MIDI Command Lane CC102–119 without consuming MIDI channel-mode CC120–127.
- Upgraded component state schema from v6 to v7 with backward-compatible defaults for v3.0 projects.
- Added v3.1 Host Scope controls to the VSTGUI resource.
- Added dependency-free C++ HostCycleScope smoke and source-contract smoke.
- Added Cubase and Studio One quick-start guides.
- No acoustic architecture, weights, or training data changed.
