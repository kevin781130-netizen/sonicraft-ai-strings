# SONICRAFT AI Strings Q4 v3.1 — Host-Native Locator Scope

v3.1 removes the export/beat-entry step for the fastest local Retake/Director workflow.
The VST3 processor requests the host's musical project position and cycle/locator range and treats that range as a live SONICRAFT performance region.

## Why this is different from v3.0 Project Bridge

v3.0 remains the persistent/editable MIDI route: it writes SONICRAFT Command Lane CC102–119 into an exported MIDI file.

v3.1 adds a second, non-destructive route:

1. select a range in the DAW;
2. set the DAW locators/loop range to that selection;
3. choose SONICRAFT **Host Scope** = Locator Retake, Locator Director, or Locator Both;
4. play/render normally.

No note, keyswitch, CC1/CC3/CC11, or Command Lane event is rewritten. The VST3 host context is the scope source.

## VST3 contract

The processor now requests:

- tempo;
- project time in quarter notes;
- cycle/locator music range;
- transport state.

When the host reports a valid locator range, the processor determines whether each processing position is inside that range.
If a locator start/end falls inside an audio block, v3.1 injects that boundary into the same timeline used for MIDI and automation so the scoped state switches at the boundary rather than waiting for a later block.

## Host Scope modes

- **Off** — v3.0/global behavior.
- **Locator Retake** — current Retake Target/Amount/Seed applies only inside the locator range; Retake is forced Off outside. Other performance settings remain global.
- **Locator Director** — inside the locator range, Host Scope Style + Host Scope Looseness override the global Director style/looseness and Phrase Director is enabled. Outside, global Director settings remain untouched.
- **Locator Both** — combines the two behaviors.

New VST automation parameters:

- `Host Scope` (`kParamHostScopeMode`, 120)
- `Host Scope Style` (`kParamHostScopeStyle`, 121)
- `Host Scope Looseness` (`kParamHostScopeLooseness`, 122)

These numeric IDs are **VST parameter IDs**, not MIDI controller numbers.
SONICRAFT deliberately does not consume MIDI CC120–127 because those are MIDI channel-mode messages.

## Cubase fast path

Cubase exposes **Locators to Selection** as the `P` key command in current Cubase 15 documentation.

Typical flow:

1. Select the MIDI/event range.
2. Press `P` to move left/right locators to the selection.
3. In SONICRAFT choose `Host Scope = Locator Retake` or `Locator Both`.
4. Set Retake Target / Amount / Seed.
5. Audition or render. Change Seed to compare another take; notes remain untouched.

Cycle playback is optional for SONICRAFT scoping: v3.1 uses the valid locator range supplied by the host, not only the Cycle Active flag.

## Studio One fast path

Set the Song loop range to the event/range you want to process, then use the same SONICRAFT Host Scope controls.
The exact shortcut can vary with Studio One version/user key map; SONICRAFT only depends on the VST3 loop/cycle range reported by the host.

## Fallback / compatibility

- If the host does not provide a valid project-time + cycle range, Host Scope fails open to the normal global v3.0 behavior instead of silently disabling the instrument.
- v3.0 Command Lane MIDI remains valid and unchanged.
- v3.0 Project Bridge remains available when a persistent, visible-in-MIDI regional edit is preferred.
- v3.1 does not require training-data/model changes.
