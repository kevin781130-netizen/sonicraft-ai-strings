# SONICRAFT AI Strings Q4 v3.2 — Live Retake Carousel

## Goal
Audition multiple neural-performance interpretations of a DAW locator range at loop speed without editing or re-importing MIDI.

## Controls
- **Host Scope**: must include Retake (`Locator Retake` or `Locator Both`) for the bank to affect the locator range.
- **Take Bank Mode**
  - `Off`: v3.1 behavior; Retake Seed is unchanged.
  - `Manual`: `Take Select` chooses A/B/C/D immediately.
  - `Auto Loop`: starts at `Take Select` and advances A→B→C→D→A on each confirmed locator/cycle wrap while the DAW cycle is active.
- **Take Select**: A/B/C/D.
- **Freeze Current Take**: in Auto Loop, stop advancing while retaining the currently active runtime take.

## Determinism
Take A is the exact Base Retake Seed. B/C/D are stable 24-bit hash derivatives of the same base seed. The same base seed + same take letter yields the same derived nonce. A fresh transport start begins at the explicitly selected Take.

## Safety rules
1. The Take Bank only changes the Retake nonce while playback is inside a valid host locator/cycle range.
2. If Host Scope does not include Retake, Take Bank is inert.
3. Outside the locator range, the user's Base Retake Seed is preserved.
4. Cycle wrap detection requires a substantial backwards project-time jump inside the same cycle window, reducing false advancement from minor host timing jitter.
5. No new MIDI CC is consumed. CC102–119 Command Lane remains unchanged; MIDI CC120–127 remain untouched.

## Cubase fast path
1. Select the phrase/events.
2. Use **P — Locators to Selection**.
3. Enable cycle.
4. SONICRAFT: Host Scope = Locator Retake or Locator Both.
5. Choose Retake Target/Amount/Base Seed.
6. Take Bank = Auto Loop.
7. Start at A/B/C/D using Take Select.
8. Freeze when the preferred take is playing.

## Studio One
Use the loop range for the target phrase, enable Host Scope Retake/Both, then use Manual or Auto Loop Take Bank. Exact host shortcut names can vary by Studio One key-command configuration; SONICRAFT uses the VST3 process-context cycle range rather than a private Studio One API.

## Architecture boundary
This feature does not change the acoustic/training model. It changes only performance-control seed selection in the host-scoped Retake path.
