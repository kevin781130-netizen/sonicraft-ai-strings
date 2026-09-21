from __future__ import annotations

from performance_planner_contract import (
    ARTICULATIONS,
    CONTINUOUS_TARGETS,
    FEATURE_NAMES,
    PLANNER_SCHEMA,
    PLANNER_VERSION,
    build_note_features,
    merge_authoritative_controls,
    prediction_record,
    validate_plan,
)


def main() -> int:
    notes = [
        {"pitch": 60, "start_beats": 0, "duration_beats": 1.0, "velocity": 80},
        {"pitch": 64, "start_beats": 1, "duration_beats": 1.0, "velocity": .72},
        {"pitch": 67, "start_beats": 2, "duration_beats": 2.0, "velocity": .76},
    ]
    features = build_note_features(notes, bpm=72, instrument=0)
    assert len(features) == 3
    assert all(len(x) == len(FEATURE_NAMES) for x in features)
    assert features[0][-2] == 1.0 and features[-1][-1] == 1.0
    assert all(0.0 <= v <= 1.0 for row in features for v in row)

    predicted = prediction_record("spiccato", {
        "dynamics": .42,
        "expression": .47,
        "legato": 0,
        "bow_change_prob": .9,
        "transition_speed": .8,
        "short_tightness": .85,
        "attack_character": .78,
        "vibrato_onset": .2,
        "vibrato_depth_cents": 4,
        "vibrato_rate_hz": 5.5,
        "vibrato_jitter": .03,
        "transition_target_ms": 50,
        "speed_profile": .4,
    })
    merged, source = merge_authoritative_controls(predicted, {
        "articulation": "legato",
        "dynamics": .91,
        "legato": 1.0,
    })
    assert merged["articulation_name"] == "legato"
    assert merged["articulation"] == ARTICULATIONS.index("legato")
    assert merged["dynamics"] == .91
    assert merged["legato"] == 1.0
    assert source["articulation"] == "written"
    assert source["dynamics"] == "written"
    assert source["transition_speed"] == "planner"

    plan = {
        "schema_version": PLANNER_SCHEMA,
        "planner_version": PLANNER_VERSION,
        "notes": [
            {"pitch": 60, "controls": merged},
        ],
    }
    validate_plan(plan)

    bad = {
        "schema_version": PLANNER_SCHEMA,
        "notes": [{"pitch": 60, "controls": dict(merged, dynamics=2.0)}],
    }
    try:
        validate_plan(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-range controls must fail validation")

    assert len(CONTINUOUS_TARGETS) >= 10
    print("performance-planner contract smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
