## v2.6 in-process boundary

The acoustically promoted model remains unchanged. v2.6 adds a native C++ inference graph and optional ONNX Runtime Session adapter so Python/localhost is no longer an architectural requirement. Native selection is fail-closed behind a SHA-256 promotion lock plus control/tensor parity, ABX, native-runtime and ultra-low-latency evidence. The existing Torch/ORT service remains the production fallback until real checkpoint parity passes.

## v2.5 ultra-low-latency boundary

The acoustic model remains unchanged. v2.5 adds a Windows IAudioClient3 event-driven output path, driver-timestamped MIDI alignment and adaptive attack/sustain render quanta. Runtime backend selection remains promotion-bound: ORT is not selected merely because it is installed. The experimental service-free ORT bundle must also remain Python/Torch-free and is not a production default until full parity promotion exists.

## v2.4 realtime-product boundary

v2.4 keeps the neural core unchanged and adds a promotion-bound runtime AUTO selector plus a rolling-window standalone product shell. AUTO uses ORT only when native promotion, footprint evidence and every bound artifact SHA still verify; otherwise it stays on Torch. The Windows shell uses Master + 11 auxiliary feeds, native MIDI/audio APIs and strict MIDI-authority defaults. Formal realtime promotion requires real non-MOCK first-audio timing evidence.

## v2.3 native-production boundary

v2.3 keeps the promoted neural core unchanged. The runtime service remains the single localhost rendering authority, while a standalone C++20 host can now use the same protocol without VST3. Room profiles may be created from rights-confirmed sweep measurements using the v2.3 capture pipeline. ORT remains opt-in until the v2.3 native promotion contract passes footprint, artifact binding, numerical parity, listener ABX, production-hardware p95 RTF, and the existing acoustic-promotion gate.

## v2.2 platform/runtime layer

v2.2 keeps the v2.0/v2.1 acoustic model unchanged and adds true host-facing multi-output plumbing: stereo Master plus eleven stereo auxiliary scoring feeds (34 channels on the localhost wire only when aux buses are active). The built-in room remains SONICRAFT clean-room geometry; `SONICRAFT_ROOM_PROFILE` or `Room/active_room_profile.json` can supply a directional profile built only from owned/explicitly licensed IRs. `ort_model_backend.py`, `control_builder_np.py`, and `stage_renderer_np.py` form a no-PyTorch deployment challenger. `renderer_service.py --backend ort` is opt-in; `auto` intentionally stays on the acoustically proven Torch path until native-runtime promotion evidence passes.

## v2.1 clean-room performance/product parity layer

The v2.1 runtime keeps the Schema-7 acoustic model unchanged and adds zero/small-state product intelligence around it: opt-in predictive dynamics and smart articulation, deterministic targeted Retake, up to 16 independent overlapping voices per string part, an eleven-feed phase-coherent virtual stage mixed through Dry / Scoring / Wide / Room perspectives, MusicXML conversion support, and `SONICRAFT_DEVICE=auto|cuda|cpu`. Smart Dynamics and Smart Articulation default OFF so authored CC/articulation remains authoritative. Retake modifies hidden performance dimensions only and never rewrites written MIDI note pitch or explicit pitch-bend. CPU fallback is functionally validated but is not claimed real-time on every laptop. The 11 feeds are internally addressable; the current VST UI exposes four perspective macros rather than a full eleven-fader/multi-output mixer.

## v2.0 schema-7 acoustic promotion integrity

Schema 7 adds no neural inference module. The consumer verifier only checks staged hashes and promotion metadata. A v2.0 pack must contain a passed Sound Forge report, acoustic-segmentation evidence, a schema-2 stereo/phase/harmonic codec tournament, a powered codec-transparency ABX, a powered generated-vs-real ABX, and a passed acoustic-promotion report. HQ, Frontier and decoder checkpoints must carry the same post-ABX `acoustic_promotion_id` plus a tensor-preserving promotion seal. Candidate checkpoints are therefore not releasable. Schema 5/6 verification remains supported for older packs.

## v1.9 schema-6 release integrity

The runtime model-pack verifier now accepts schema 6 and fail-closes on tampered/missing Sound Forge, codec-tournament or codec-ABX evidence. No Sound Forge or evaluation code is imported by the consumer renderer; only the small JSON/hash integrity check is added.

# SONICRAFT Shadow Renderer Runtime v1.6

The VST audio callback never runs CUDA, file I/O, sockets, model loading, or allocation-heavy inference.
It keeps the low-latency LIVE preview active while a worker thread sends phrase snapshots to a local-only
renderer service on `127.0.0.1:49337`. Completed stereo float32 phrases are installed into a lock-free
4-slot cache and crossfaded into playback.

Release backend priority is intentionally strict: an actual renderer checkpoint and its manifest-approved decoder
must exist in the selected install folder under `Models`. If they do not, the service reports
`MODEL_NOT_READY` and the plug-in stays in LIVE preview. The `--mock` backend exists only for IPC QA and must
not be treated as an acoustic model.

Expected v1.6 roles are manifest-driven, not filename-driven:
- `compact` / `hq`: rectified-flow renderer checkpoints
- `string_vae64`: preferred 48 kHz / 64-d compact decoder
- legacy only: `dac` + `dac_base`

The preferred VAE64 path has **no `descript-audio-codec` runtime dependency**. DAC is installed lazily only when a legacy model pack is explicitly selected.

The protocol is binary and bounded. The service binds loopback only. Phrase renders are content-addressed in
`Cache/`, so second playback of an unchanged phrase can be a cache hit.


## v1.5 compact-flow runtime additions (retained)

- Deterministic phrase seed is derived from request/events/model fingerprint, so cache eviction does not randomly change the same render.
- Long phrases use fixed-size tiles (default 10 s, 1 s overlap) and crossfade after decode in audio space.
- Euler remains the default rectified-flow solver; Heun is an A/B challenger for low-step schedules.
- MIDI-authority CFG is available but defaults to scale 1.0 until blind tests approve stronger guidance.
- Inference settings are included in the render fingerprint so changing solver/CFG/tile settings cannot accidentally reuse an incompatible cache entry.
- Third-party MIT analyzers/reference repos are development-only and are not runtime dependencies.


## v1.6 codec-generic runtime

Renderer checkpoints now declare `latent_ch`, `latent_hz`, `codec_kind` and `codec_sample_rate`. The runtime supports the legacy `dac44` path and the new `strings_vae64` decoder role, and allocates RF noise from model geometry instead of fixed `1024 x 25 Hz` assumptions. Only one selected codec is allowed in a model pack.


## v1.6 frontier entry: zero-weight quartet coordination

Assist/Auto now derive ensemble-entry and supporting-voice context from the four MIDI parts and coordinate only the hidden bow-change prior. This adds no model weights and does not modify written pitch, note gate/timing, velocity, articulation, or explicit user CC curves. Manual mode is unchanged.
