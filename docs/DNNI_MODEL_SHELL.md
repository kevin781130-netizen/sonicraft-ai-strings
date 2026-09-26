# SONICRAFT DNNI Model Shell

`runtime/dnni_model_shell.py` is the local model-container boundary for user-provided DNNI v4 files.

It is intentionally a **container/identity loader**, not a proprietary renderer clone. It:

- validates DNNI v4 magic/version/header size;
- parses the four `<offset,size>` section pairs directly from the file header;
- validates ordering, bounds, overlap, and the observed 256-byte trailer;
- exposes bounded streaming readers for each section;
- hashes the complete file and the `weights` section without loading the whole model into RAM;
- matches models against `training/configs/dnni_source_labels.json`;
- identifies known instruments first by full-file SHA-256 and then by exact weights SHA-256;
- scans a private directory and builds a role-addressable catalog.

It deliberately does **not** guess tensor names/shapes, decrypt content, bypass signatures/licensing, or claim compatibility with any proprietary renderer.

## Private local model folder

Use `models/dnni/`. The repository ignores this directory; keep original `.dnni` and companion files local.

## Windows

Inspect one model:

    DNNI_MODEL_SHELL.bat inspect models\dnni\MODEL.dnni

JSON output:

    DNNI_MODEL_SHELL.bat inspect models\dnni\MODEL.dnni --json

Scan all local models:

    DNNI_MODEL_SHELL.bat scan models\dnni

## Python API

    from runtime.dnni_model_shell import DnniModelHandle, load_registry

    registry = load_registry("training/configs/dnni_source_labels.json")
    model = DnniModelHandle("models/dnni/example.dnni")
    identity = model.match_registry(registry)

    print(identity.instrument_role)
    print(model.header.sections)
    print(model.weights_sha256)

    with model.open_section("weights") as weights:
        first_4096 = weights.read(4096)

The stable API boundary for future SONICRAFT renderers is `DnniModelHandle`: later rendering work can consume opaque section streams without changing discovery, identity, provenance, or file validation.
