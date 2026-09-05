# v4.1 Strings Per-Note Expression

## 4×4 String Voice Bus
The first voice preserves the legacy quartet channel:
- Vln I: CH1 + CH5/6/7
- Vln II: CH2 + CH8/9/10
- Viola: CH3 + CH11/12/13
- Cello: CH4 + CH14/15/16

This yields four explicit independently-controlled MIDI lanes per string part.

## Per-lane controls
- CC21: 4-bit Expression Stack (Accent=1, Legato=2, Tenuto=4, Expressive=8)
- CC22: Dynamics
- CC23: Vibrato
- CC24: Transition Speed
- CC25: Attack Character
- CC26: Short Tightness

Base articulation remains the existing keyswitch C0–B0 vocabulary.

## HQ transport
The existing one-byte event `part` field is extended backward-compatibly:
- 0..3 = historical global part events
- encoded values >=4 carry part + explicit voice-lane identity

Renderer service decodes the identity before the model pipeline. Explicit lane controls are routed only to their own monophonic polyphony lane. The event articulation byte packs:
- low nibble = trained base articulation
- high nibble = expression modifier stack

The neural embedding always receives the decoded 0..11 base ID.

## Retake
Explicit lanes add their lane identity only to the deterministic Retake key, preventing two overlapping notes in the same string part from receiving identical hidden drift. Legacy events have no lane identity and keep the prior deterministic contract.

## Honest limit
Four explicitly expressed overlapping notes per part are supported. A fifth overlap causes deterministic lane reuse plus `string_voice_lane_overflow` in the score manifest.
