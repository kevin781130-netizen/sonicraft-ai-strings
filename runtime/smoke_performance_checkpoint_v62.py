from pathlib import Path
import tempfile,json,copy

from compile_musicxml_strings_v62 import compile_file
from evidence_store_v60 import UnifiedEvidenceStoreV60,NAMESPACES,empty_namespace_payload_v60
from performance_checkpoint_v62 import (
    create_compile_checkpoint_v62,verify_checkpoint_v62,replay_verify_checkpoint_v62,
    restore_checkpoint_environment_v62,load_checkpoint_v62,release_checkpoint_pin_v62,
    finalize_checkpoint_v62
)
from string_repair_policy_v49 import RepairPolicyMemoryV49
from acoustic_runtime_provenance_v62 import capture_acoustic_runtime_provenance_v62,export_in_toto_slsa_envelope_v62
import hashlib,shutil

XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list>\n<score-part id="P1"><part-name>Violin 1</part-name></score-part>\n<score-part id="P2"><part-name>Violin 2</part-name></score-part>\n<score-part id="P3"><part-name>Viola</part-name></score-part>\n<score-part id="P4"><part-name>Cello</part-name></score-part>\n</part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="90"/></direction>\n<note><pitch><step>G</step><octave>3</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>E</step><octave>6</octave></pitch><duration>4</duration><notations><slur type="continue"/><glissando type="start"/></notations></note>\n<note><pitch><step>A</step><octave>3</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>\n<note><pitch><step>D</step><octave>6</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note>\n</measure>\n<measure number="2"><note><rest/><duration>8</duration></note>\n<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>B</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note></measure>\n</part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n</score-partwise>'

def write_json(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,sort_keys=True,indent=2)+"\n",encoding="utf-8")

with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    score=td/"checkpoint.musicxml";score.write_text(XML)
    policy=td/"repair_policy.json"
    # Materialize default policy so restore/backup behavior can be tested explicitly.
    pm=RepairPolicyMemoryV49(policy)
    write_json(policy,pm._payload())

    # Minimal fake model pack: provenance must bind actual bytes, not only the manifest string.
    model_dir=td/"Models";model_dir.mkdir()
    weight=model_dir/"fixture_weights.bin";weight.write_bytes(b"v62-fixture-weights")
    wsha=hashlib.sha256(weight.read_bytes()).hexdigest()
    write_json(model_dir/"release_model_manifest.json",{
        "schema":1,"product":"SONICRAFT AI Strings Q4","version":"fixture",
        "commercial_safe":True,"release_approved":True,
        "files":[{"name":weight.name,"role":"compact","sha256":wsha}]
    })
    acoustic=capture_acoustic_runtime_provenance_v62(
        model_dir=model_dir,backend="auto",mock=True,sample_rate=48000,
        chunk_seconds=40.0,overlap_seconds=.75,local_context=.85,max_local_context_seconds=28.0)
    assert acoustic["identity"]["model_environment"]["files"][0]["hash_match"]
    envelope=export_in_toto_slsa_envelope_v62(acoustic,"fixture")
    assert envelope["_type"]=="https://in-toto.io/Statement/v1"
    assert envelope["predicateType"]=="https://slsa.dev/provenance/v1"

    paths={n:td/(n+".json") for n in NAMESPACES}
    store=UnifiedEvidenceStoreV60(td/"evidence_store.json")
    boot=store.bootstrap_or_recover(paths)
    assert boot["mode"]=="bootstrap"
    input_head=store.head

    out=td/"checkpoint_SONICRAFT_STRINGS_v62_R1.mid"
    comp=compile_file(score,out,policy,1)
    cp,cpp=create_compile_checkpoint_v62(comp,score,store,1,td/"R01.performance_checkpoint.json",acoustic_runtime=acoustic)
    assert cpp.exists()
    assert cp["input_state"]["evidence"]["commit_id"]==input_head
    assert cp["input_state"]["repair_policy"]["profile_hash"]==comp["policy_snapshot"].profile_hash
    assert cp["input_state"]["conductor_intent_hash"]==comp["conductor_intent"].intent_hash
    assert set(cp["compile_artifacts"])=={"midi_D","midi_A","midi_B","midi_C","score_json","critic_json","policy_json","conductor_json","steering_json","archetype_json","mixture_json","judge_queue_json"}

    runtime_kwargs={"model_dir":model_dir,"backend":"auto","mock":True,"sample_rate":48000,
                    "chunk_seconds":40.0,"overlap_seconds":.75,"local_context":.85,"max_local_context_seconds":28.0}
    v=verify_checkpoint_v62(cpp,score,store,current_policy_path=policy,acoustic_runtime_kwargs=runtime_kwargs)
    assert v["source_ok"] and v["compiler_code_ok"] and v["evidence_commit_ok"],v
    assert v["current_policy_matches_input"] and v["compile_artifacts_ok"],v
    assert v["acoustic_runtime_ok"] and v["acoustic_replay_context_ready"],v
    assert v["replay_ready"]

    # Same musical/control environment compiled in a different local directory MUST produce
    # the same checkpoint ID even though raw JSON path bytes differ.
    other=td/"another_location";other.mkdir()
    score2=other/"renamed_copy.musicxml";score2.write_text(XML)
    policy2=other/"another_policy_path.json";write_json(policy2,pm._payload())
    comp2=compile_file(score2,other/"checkpoint_SONICRAFT_STRINGS_v62_R1.mid",policy2,1)
    other_model=other/"Models";shutil.copytree(model_dir,other_model)
    acoustic2=capture_acoustic_runtime_provenance_v62(model_dir=other_model,backend="auto",mock=True,sample_rate=48000,chunk_seconds=40.0,overlap_seconds=.75,local_context=.85,max_local_context_seconds=28.0)
    assert acoustic2["binding_sha256"]==acoustic["binding_sha256"]
    cp2,cpp2=create_compile_checkpoint_v62(comp2,score2,store,1,other/"same_state.performance_checkpoint.json",acoustic_runtime=acoustic2)
    assert cp2["checkpoint_id"]==cp["checkpoint_id"],(cp["checkpoint_id"],cp2["checkpoint_id"])
    assert cp2["compile_artifacts"]["policy_json"]["raw_sha256"]!=cp["compile_artifacts"]["policy_json"]["raw_sha256"]
    assert cp2["compile_artifacts"]["policy_json"]["normalized_sha256"]==cp["compile_artifacts"]["policy_json"]["normalized_sha256"]
    # Two checkpoint files with the same ID share one evidence pin tag, not duplicate retention tags.
    assert store.pinned_commits()[input_head].count("checkpoint:"+cp["checkpoint_id"])==1

    replay=replay_verify_checkpoint_v62(cpp,score,store,acoustic_runtime_kwargs=runtime_kwargs)
    assert replay["passed"],replay
    assert replay["conductor_intent_hash_actual"]==replay["conductor_intent_hash_expected"]
    assert all(x["ok"] for x in replay["artifacts"].values())
    assert replay["acoustic_runtime_match"] is True

    # Acoustic drift must be explanatory without breaking deterministic compile replay readiness.
    drift_kwargs=dict(runtime_kwargs);drift_kwargs["sample_rate"]=44100
    drift=verify_checkpoint_v62(cpp,score,store,current_policy_path=policy,acoustic_runtime_kwargs=drift_kwargs)
    assert drift["compile_replay_ready"] is True and drift["acoustic_runtime_ok"] is False,drift
    assert any(x["path"]=="render_config.sample_rate" for x in drift["acoustic_runtime"]["differences"]),drift


    # Artifact tamper is detected by Verify.
    midi=Path(comp["midi_B"]);original=midi.read_bytes();midi.write_bytes(original+b"tamper")
    bad=verify_checkpoint_v62(cpp,score,store,current_policy_path=policy,acoustic_runtime_kwargs=runtime_kwargs)
    assert not bad["compile_artifacts_ok"]
    assert not bad["artifacts"]["midi_B"]["ok"]
    midi.write_bytes(original)
    assert verify_checkpoint_v62(cpp,score,store,current_policy_path=policy,acoustic_runtime_kwargs=runtime_kwargs)["compile_artifacts_ok"]

    # Move both Evidence and Policy forward after the checkpoint.
    u=json.loads(paths["utility_v55"].read_text());u["generation"]=1
    u["contexts"]={"build|transition":{"total_windows":1.0,"slots":{}}}
    write_json(paths["utility_v55"],u)
    c2=store.capture_legacy(paths,"after_checkpoint")
    assert c2["committed"] and store.head!=input_head
    pm2=RepairPolicyMemoryV49(policy)
    learned=pm2.learn("B",.08,.9,.9)
    assert learned["learned"]
    assert pm2.snapshot().profile_hash!=cp["input_state"]["repair_policy"]["profile_hash"]

    # Advance enough transactions that normal compact(retain=2) would drop the checkpoint input
    # commit if it were not pinned.
    for gi in range(2,7):
        m=json.loads(paths["mixture_v59"].read_text());m["generation"]=gi
        m["edges"]={f"edge_{{gi}}":{"trust":round(.9-gi*.01,3)}}
        write_json(paths["mixture_v59"],m)
        cc=store.capture_legacy(paths,f"advance_{{gi}}")
        assert cc["committed"]
    live_head=store.head
    compacted=store.compact(retain=2)
    assert store._commit_by_id(input_head) is not None,(compacted,store.status())
    assert input_head in store.pinned_commits(),store.status()
    assert len(store.commits)>=3  # 2 recent + pinned checkpoint commit

    # Verify is still replay-ready but reports that the live policy has advanced.
    advanced=verify_checkpoint_v62(cpp,score,store,current_policy_path=policy,acoustic_runtime_kwargs=runtime_kwargs)
    assert advanced["replay_ready"] is True
    assert advanced["current_policy_matches_input"] is False
    # Replay remains non-destructive and uses the embedded old policy snapshot.
    replay2=replay_verify_checkpoint_v62(cpp,score,store,acoustic_runtime_kwargs=runtime_kwargs)
    assert replay2["passed"],replay2
    assert store.head==live_head
    assert RepairPolicyMemoryV49(policy).snapshot().profile_hash==pm2.snapshot().profile_hash

    # Explicit restore rolls Evidence + Policy back together and creates a policy backup.
    restored=restore_checkpoint_environment_v62(cpp,store,paths,policy,True)
    assert restored["restored"]
    assert restored["evidence_commit"]==input_head
    assert store.head==input_head
    assert restored["policy_backup"] and Path(restored["policy_backup"]).exists()
    assert RepairPolicyMemoryV49(policy).snapshot().profile_hash==cp["input_state"]["repair_policy"]["profile_hash"]
    assert store.verify_legacy(paths)["all_match"]

    # Explicit release removes the retention pin; checkpoint file remains readable but future
    # compaction may remove its evidence commit.
    rel=release_checkpoint_pin_v62(cpp,store)
    assert rel["released"],rel
    assert input_head not in store.pinned_commits(),store.status()

    # Checkpoint identity remains valid after output-state finalization is absent/present.
    loaded=load_checkpoint_v62(cpp)
    assert loaded["checkpoint_id"]==cp["checkpoint_id"]

    # Finalized result binding is independently tamper-evident.
    finalized=finalize_checkpoint_v62(
        cpp,store,policy,
        decision_summary={"mode":"fixture_final","winner":"B","pair_verify":{"passed":True}},
        artifacts={"midi_B":comp["midi_B"]},
        status="fixture_finalized"
    )
    assert load_checkpoint_v62(cpp)["result_binding_sha256"]==finalized["result_binding_sha256"]
    raw=json.loads(cpp.read_text());raw["output_state"]["decision_summary"]["winner"]="A"
    cpp.write_text(json.dumps(raw,sort_keys=True,indent=2)+"\n")
    try:
        load_checkpoint_v62(cpp)
        raise AssertionError("finalized output-state tamper accepted")
    except ValueError as ex:
        assert "checkpoint_result_binding_mismatch" in str(ex),ex
    # Restore the valid finalized checkpoint for the remaining identity assertion/report.
    cpp.write_text(json.dumps(finalized,sort_keys=True,indent=2)+"\n")
    assert load_checkpoint_v62(cpp)["checkpoint_id"]==cp["checkpoint_id"]

    print("SONICRAFT v6.2 checkpoint capture/verify/replay/tamper/restore smoke OK",
          "checkpoint",cp["checkpoint_id"],"input_head",input_head,
          "artifacts",len(cp["compile_artifacts"]),"cross_path_id_stable",cp2["checkpoint_id"]==cp["checkpoint_id"],
          "pinned_compact_commits",compacted["commits"],
          "backup",Path(restored["policy_backup"]).name,"pin_released",rel["released"],
          "acoustic_binding",acoustic["binding_sha256"][:16],"runtime_drift_explained",True,
          "result_binding_tamper_rejected",True)
