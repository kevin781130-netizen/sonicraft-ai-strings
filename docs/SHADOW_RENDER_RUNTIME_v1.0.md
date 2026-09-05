# Shadow Render Runtime v1.0

v1.0 closes the previous product gap between the VST3 front end and the local neural renderer.

## Runtime topology

```text
Cubase audio thread
  -> LIVE preview (always immediate)
  -> fixed lock-free event ring / fixed cache reads only

VST worker thread
  -> localhost 127.0.0.1:49337
  -> phrase request snapshots

Shared Renderer Service
  -> Compact model for AUTO (preferred, 8 Euler steps by default)
  -> HQ model for HQ mode (preferred, 24 Euler steps by default)
  -> strings-fine-tuned DAC decoder
  -> content-addressed phrase cache

Completed stereo phrase
  -> 4-slot lock-safe cache
  -> ~22 ms edge crossfade into the VST output
```

CUDA, sockets, files, model loading and Python never run in the Cubase audio callback.
If the service is unavailable or release weights are missing, the VST stays on LIVE preview.

## Multi-instance behavior

One local service owns the CUDA models and decoder. Multiple VST instances connect to the same service instead of loading duplicate GPU models. TCP clients are accepted concurrently; CUDA inference is serialized by a shared render lock so separate plug-in instances cannot race independent CUDA contexts.

## Cache

Requests are content-addressed after request-id normalization. Repeating the same phrase/control request can return a cache hit even when the transport issues a new request id. Cache size defaults to 4 GiB and is pruned toward 85% of the limit when exceeded.

## Musical authority

The request carries exact note/timing/articulation plus CC1, CC3, CC11, CC20, CC7, CC10, CC64, CC68, CC91 and pitch bend state. The neural model is allowed to infer performance micro-detail, not silently rewrite the MIDI score.

## Tempo / look-ahead limitation

`ProcessContext.projectTimeSamples`, project musical position and tempo are used as host authority when available. Standard VST3 processing does **not** give a plug-in arbitrary future MIDI events that Cubase has not delivered yet. Therefore v1.0 Look Ahead controls rolling context, render tail and cache aggressiveness; it does not pretend to read future bars from the DAW. Full future-context rendering requires an offline/pre-render pass or already cached material.

## Release-weight policy

Normal runtime mode never substitutes the engineering mock renderer for missing weights. It reports MODEL_NOT_READY and leaves LIVE active. `--mock` exists only for IPC/crossfade QA.
