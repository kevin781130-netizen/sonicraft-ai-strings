#!/usr/bin/env python3
from __future__ import annotations

"""Prepare the first SONICRAFT DNNI offline-render experiment.

This produces a deterministic experiment manifest. It does not claim audio inference
is available until graph ops, tensor shapes, input schema and output decoder are known.
"""

import argparse
import json
from pathlib import Path
import sys

from dnni_model_shell import DnniModelCatalog, load_registry

SHARED_CORE_BYTES = 126_227_640
GROUP_BYTES = 784_352
SUBBLOCK_BYTES = 196_088


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dir", nargs="?", default="models/dnni")
    ap.add_argument("--registry", default="training/configs/dnni_source_labels.json")
    ap.add_argument("--dtype-map", default=None)
    ap.add_argument("--shared-regions", default=None)
    ap.add_argument("--tensor-map", default=None)
    ap.add_argument("--projection-bank", default=None)
    ap.add_argument("--graph-fragment", default=None)
    ap.add_argument("--operation-constraints", default=None)
    ap.add_argument("--recurrent-signature", default=None)
    ap.add_argument("--out", default="violin_a4_golden_path.json")
    args = ap.parse_args()

    registry = load_registry(args.registry)
    catalog = DnniModelCatalog(registry)
    models = catalog.scan(args.model_dir, recursive=True)
    violin = None
    for m in models:
        if m.registry_match and m.registry_match.instrument_role == "violin":
            violin = m
            break
    if violin is None:
        raise SystemExit("Confirmed violin DNNI was not found in the model directory.")

    weights = violin.section("weights")
    tail = weights.size - SHARED_CORE_BYTES
    if tail < GROUP_BYTES or tail % GROUP_BYTES:
        raise SystemExit("Violin weights do not match the observed shared-core/tail layout.")

    def maybe_json(path):
        return json.loads(Path(path).read_text(encoding="utf-8")) if path else None

    dtype_map = maybe_json(args.dtype_map)
    shared_regions = maybe_json(args.shared_regions)
    tensor_map = maybe_json(args.tensor_map)
    projection_bank = maybe_json(args.projection_bank)
    graph_fragment = maybe_json(args.graph_fragment)
    operation_constraints = maybe_json(args.operation_constraints)
    recurrent_signature = maybe_json(args.recurrent_signature)

    result = {
        "schema": "sonicraft-dnni-golden-path-v1",
        "experiment": "violin_a4_sustain_single_candidate_mic_offline",
        "model": {
            "path": str(violin.path),
            "source_uuid": violin.registry_match.source_uuid,
            "label_en": violin.registry_match.label_en,
            "label_zh": violin.registry_match.label_zh,
            "source_sha256": violin.source_sha256,
            "weights_sha256": violin.weights_sha256,
            "weights_offset": weights.offset,
            "weights_bytes": weights.size,
        },
        "input_target": {
            "midi_pitch": 69,
            "note_name": "A4",
            "articulation": "sustain",
            "tempo_bpm": 120.0,
            "duration_beats": 2.0,
            "velocity": 0.70,
            "dynamics": 0.65,
            "expression": 1.0,
            "vibrato": 0.50,
            "pitch_bend_cents": 0.0,
        },
        "numeric_regions": {
            "shared_core": {
                "relative_offset": 0,
                "absolute_offset": weights.offset,
                "bytes": SHARED_CORE_BYTES,
            },
            "candidate_mic_group_0": {
                "relative_offset": SHARED_CORE_BYTES,
                "absolute_offset": weights.offset + SHARED_CORE_BYTES,
                "bytes": GROUP_BYTES,
                "subblocks": [
                    {
                        "index": i,
                        "relative_offset": SHARED_CORE_BYTES + i * SUBBLOCK_BYTES,
                        "absolute_offset": weights.offset + SHARED_CORE_BYTES + i * SUBBLOCK_BYTES,
                        "bytes": SUBBLOCK_BYTES,
                    }
                    for i in range(4)
                ],
            },
            "candidate_mic_group_count": tail // GROUP_BYTES,
        },
        "evidence_bundle": {
            "dtype_map": dtype_map,
            "shared_regions": shared_regions,
            "tensor_map": tensor_map,
            "projection_bank": projection_bank,
            "graph_fragment": graph_fragment,
            "operation_constraints": operation_constraints,
            "recurrent_signature": recurrent_signature,
        },
        "ready_for_audio_inference": False,
        "blocking_unknowns": [
            "graph operation direction/order beyond the verified dimension fragment",
            "nonlinear activation/state-update semantics",
            "exact note/phrase conditioning tensor schema",
            "output representation and acoustic decoder",
            "candidate mic-tail semantic mapping",
        ],
        "next_success_gate": (
            "Produce one finite offline output tensor from the verified violin model for this "
            "fixed A4/Sustain request without invoking proprietary product code."
        ),
    }

    out = Path(args.out)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
