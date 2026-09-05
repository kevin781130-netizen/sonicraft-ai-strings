# SONICRAFT v5.1 Selective Phrase Search / Local Repair Rendering

## Why
v5.0 closes the self-correcting loop but pays for four whole-song renders each round. Most performance-control problems are local.

v5.1 searches Critic locations first, then spends Shadow Render / Audio Judge compute only where a repair is actually under consideration.

## Search inputs
The selector combines:
- Critic severity and dimension;
- source-note IDs;
- v4.7 phrase IDs;
- latent bow reserve / transition / gesture / ensemble risks;
- low-weight A/B/C repair edit locations.

Repair edits are deliberately lower weight than real Critic evidence so a globally-generated candidate does not make every clean phrase look broken.

## Window merging
Overlapping problem phrases from different string sections become one ensemble window. This keeps quartet context during local judging.

## Local render contract
Renderer Service receives the entire event history and an absolute sample range. The local core is rendered with pre/post context and then cropped for Judge scoring.

The saved local audition WAV receives only a tiny edge fade. Judge uses the raw unfaded core.

## Selective merge contract
D Original is the base MIDI. For each accepted window:
- ordinary channel events inside the phrase come from the local winner;
- compiler pre-roll CC/keyswitch events can be replaced;
- note-offs and Gesture close state at the end boundary can be replaced;
- a new note/CC beginning a back-to-back unselected phrase on exactly the end tick remains D;
- conductor/meta events always remain D.

Final master audio is not assembled from local WAVs. The merged MIDI is rendered once at full length.

## Policy evidence
Local winners are duration/margin weighted. A global Repair Policy update requires one strategy to hold at least 60% of the weighted evidence. Mixed phrase winners remain local and do not force one global strategy.

## Fallback
Any ambiguous local winner invalidates the local assumption for that round and triggers the full v5.0-style A/B/C/D render/Judge path.

This deliberately prioritizes correctness over compute savings.
