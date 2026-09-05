# v4.0 Score & Expression Graph — Strings Scope

The semantic graph sits between MusicXML/MXL and SONICRAFT performance MIDI.

Preserved:
- tempo map
- time signatures
- key signatures
- string part identity
- voice/staff
- chords
- tie merge
- slur/legato intent
- dynamics and wedge context
- base articulation
- expression stack
- technical markings
- unsupported string-technique warnings

Current acoustic base vocabulary remains the established 12 classes. `col legno`, `sul ponticello`, `sul tasto` and other unavailable acoustic techniques are not silently substituted.

Compressed `.mxl` is supported through its container rootfile.
