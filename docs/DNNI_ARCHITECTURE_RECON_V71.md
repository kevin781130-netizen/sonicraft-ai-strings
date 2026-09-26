# DNNI architecture reconstruction — structural phase

This phase intentionally separates **verified structure** from **unknown proprietary semantics**.

## What the 15-model comparison established

Across the 15 confirmed DNNI v4 sources, the weights region has three observed sizes. Their pairwise size deltas share a fixed greatest common divisor, which identifies a repeatable variable-tail group.

The probe also detects a smaller repeated subblock cadence from large zero-run boundaries. For the current 15-model set, the observed relationship is:

- one shared weights prefix;
- a variable tail made of fixed-size groups;
- four repeated subblocks per candidate group;
- observed group counts of 8, 9 and 11.

Dreamtonics publicly documents that Instrument X expansions were recorded with 8 to 11 microphones. That external fact makes a per-microphone interpretation a strong **hypothesis**, not a decoded fact.

The probe also reports exact zero gaps shared by every model and an auxiliary header counter at byte offset 132 that changes with the variable-tail group count.

## Run

    PROBE_DNNI_ARCHITECTURE.bat models\dnni --out models\dnni\architecture_probe.json

The output contains only offsets, sizes, counts, labels and hashes derived from local user-provided files. No proprietary model bytes are written into Git.

## Runtime use

The next renderer adapter may safely depend on:

- DNNI v4 container boundaries;
- the shared-core / variable-tail split produced by this probe;
- fixed tail group/subblock sizes when re-verified against the local model;
- model identity from the source registry.

It must **not** yet depend on invented tensor names/shapes or assume the repeated tail is directly executable FP16 state. Numeric interpretation remains a separate evidence gate.
