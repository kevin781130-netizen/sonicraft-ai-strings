"""SONICRAFT v6.1 Reproducible Performance Checkpoint / Policy-Evidence Binding.

Project-local checkpoint layer. Unlike the v6.0 cross-song Evidence Store, a checkpoint is allowed
to contain a source-score SHA-256 and artifact fingerprints because it exists to reproduce one
project's generation environment.

A checkpoint binds:
- source score SHA-256
- SONICRAFT release / compiler code fingerprint
- v6.0 Evidence Store input HEAD + namespace hashes
- exact v4.9 Repair Policy snapshot used by compile
- Conductor Intent hash
- Candidate Steering intent hash
- deterministic compile artifact hashes (D/A/B/C MIDI + key JSON sidecars)

It never embeds audio or MIDI bytes.

Replay Verify is non-destructive:
- policy is reconstructed in a temp directory;
- current Evidence Store is read-only verified;
- score is recompiled in a temp directory;
- deterministic hashes are compared.

Explicit Restore is separate and intentionally mutating:
- rollback v6.0 legacy evidence files to the checkpoint input commit;
- restore exact Repair Policy payload;
- create a local policy backup first when a policy file exists.
"""
from __future__ import annotations
from pathlib import Path
import argparse,copy,hashlib,json,os,tempfile

from evidence_store_v60 import UnifiedEvidenceStoreV60,_atomic_write
from string_repair_policy_v49 import RepairPolicyMemoryV49,KEYS

CHECKPOINT_SCHEMA=1
CHECKPOINT_VERSION="6.1"
CODE_FILES=(
    "runtime/compile_musicxml_strings_v61.py",
    "runtime/score_expression_graph_v40.py",
    "runtime/string_physical_graph_v42.py",
    "runtime/string_constraint_solver_v43.py",
    "runtime/string_ensemble_solver_v44.py",
    "runtime/string_gesture_graph_v45.py",
    "runtime/string_transition_graph_v46.py",
    "runtime/string_phrase_longline_v47.py",
    "runtime/string_performance_critic_v48.py",
    "runtime/string_repair_policy_v49.py",
    "runtime/conductor_intent_v53.py",
    "runtime/conductor_candidate_steering_v54.py",
    "runtime/archetype_mixture_v59.py",
    "runtime/evidence_store_v60.py",
    "runtime/performance_checkpoint_v61.py",
)
ARTIFACT_KEYS=(
    "midi_D","midi_A","midi_B","midi_C",
    "score_json","critic_json","policy_json","conductor_json","steering_json",
    "archetype_json","mixture_json","judge_queue_json",
)
VOLATILE_JSON_KEYS={
    "source_score","queue_dir","policy_path","persistent_policy_path",
}


def _sha_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def _canonical(obj)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")


def _root()->Path:
    return Path(__file__).resolve().parents[1]


def _norm_json(obj):
    if isinstance(obj,dict):
        out={}
        for k,v in obj.items():
            if str(k) in VOLATILE_JSON_KEYS:
                # Machine-specific path location is not part of deterministic musical identity.
                out[k]="@PATH@" if isinstance(v,str) else v
            else:
                out[k]=_norm_json(v)
        return out
    if isinstance(obj,list):return [_norm_json(x) for x in obj]
    return obj


def file_fingerprint_v61(path):
    p=Path(path)
    raw=p.read_bytes()
    row={"raw_sha256":_sha_bytes(raw),"bytes":len(raw)}
    if p.suffix.lower()==".json":
        try:
            obj=json.loads(raw.decode("utf-8"))
            row["normalized_sha256"]=_sha_bytes(_canonical(_norm_json(obj)))
            row["kind"]="json"
        except Exception:
            row["normalized_sha256"]=row["raw_sha256"];row["kind"]="binary"
    else:
        row["normalized_sha256"]=row["raw_sha256"];row["kind"]="binary"
    return row


def code_fingerprint_v61(project_root=None):
    root=Path(project_root or _root())
    rows={}
    for rel in CODE_FILES:
        p=root/rel
        if not p.is_file():raise FileNotFoundError(f"checkpoint_code_file_missing:{rel}")
        rows[rel]=_sha_bytes(p.read_bytes())
    digest=_sha_bytes(_canonical(rows))
    version=(root/"VERSION").read_text(encoding="utf-8").strip() if (root/"VERSION").exists() else "unknown"
    return {"release_version":version,"sha256":digest,"files":rows}


def policy_payload_from_snapshot_v61(snapshot):
    return {
        "version":1,
        "evidence":round(float(snapshot.evidence),9),
        "generation":int(snapshot.generation),
        "values":{k:round(float(snapshot.values[k]),9) for k in KEYS},
    }


def policy_binding_v61(snapshot):
    payload=policy_payload_from_snapshot_v61(snapshot)
    profile=RepairPolicyMemoryV49._hash(payload)
    if profile!=str(snapshot.profile_hash):
        raise ValueError(f"policy_profile_hash_mismatch:{profile}!={snapshot.profile_hash}")
    return {
        "generation":int(snapshot.generation),
        "evidence":round(float(snapshot.evidence),9),
        "confidence":round(float(snapshot.confidence),9),
        "profile_hash":profile,
        "payload_sha256":_sha_bytes(_canonical(payload)),
        "payload":payload,
    }


def _artifact_bindings(comp):
    out={}
    for key in ARTIFACT_KEYS:
        p=Path(comp[key])
        out[key]={"file_name":p.name,**file_fingerprint_v61(p)}
    return out


def _evidence_binding(store:UnifiedEvidenceStoreV60,commit_id=None):
    cid=commit_id or store.head
    if not cid:raise ValueError("evidence_store_has_no_head")
    c=store._commit_by_id(cid)
    if not c:raise KeyError(f"evidence_commit_missing:{cid}")
    ns=copy.deepcopy(c.get("namespaces",{}))
    if set(ns)!={"utility_v55","audit_v56","similarity_v57","archetype_v58","mixture_v59"}:
        raise ValueError("evidence_commit_namespace_set_invalid")
    # Force blob/hash validation now, not later.
    for name,row in ns.items():
        obj=store.read_commit_namespace(cid,name)
        if _sha_bytes(_canonical(obj))!=row["sha256"]:
            raise ValueError(f"evidence_namespace_hash_mismatch:{name}")
    return {"commit_id":cid,"namespaces":ns,"store_schema":1}


def _checkpoint_identity_projection_v61(payload_without_id):
    """Return only path-independent immutable fields that define checkpoint identity."""
    q=copy.deepcopy(payload_without_id)
    q["output_state"]=None
    # Source content is authoritative; local filename is metadata only.
    if isinstance(q.get("source"),dict):
        q["source"].pop("file_name",None)
    ev=q.get("input_state",{}).get("evidence",{})
    if isinstance(ev,dict):ev["pin_tag"]="@CHECKPOINT_PIN@"
    # JSON raw bytes may differ only because machine paths differ. Keep raw SHA in the payload for
    # forensics, but identity is based on normalized JSON SHA. Binary/MIDI raw SHA remains exact.
    for row in (q.get("compile_artifacts") or {}).values():
        if row.get("kind")=="json":
            row.pop("raw_sha256",None)
            row.pop("bytes",None)
    return q


def checkpoint_id_v61(payload_without_id):
    return _sha_bytes(_canonical(_checkpoint_identity_projection_v61(payload_without_id)))[:24]


def create_compile_checkpoint_v61(comp,source_score,evidence_store,round_index,out_path=None,project_root=None):
    source=Path(source_score).resolve()
    if not source.is_file():raise FileNotFoundError(source)
    evidence=_evidence_binding(evidence_store,evidence_store.head)
    policy=policy_binding_v61(comp["policy_snapshot"])
    intent=comp["conductor_intent"]
    steering=comp["steering_report"]
    artifact_bindings=_artifact_bindings(comp)
    body={
        "schema":CHECKPOINT_SCHEMA,
        "version":CHECKPOINT_VERSION,
        "kind":"round_compile_checkpoint",
        "round_index":int(round_index),
        "source":{"sha256":_sha_bytes(source.read_bytes()),"bytes":source.stat().st_size,
                  "file_name":source.name},
        "compiler":code_fingerprint_v61(project_root),
        "input_state":{
            "evidence":evidence,
            "repair_policy":policy,
            "conductor_intent_hash":str(intent.intent_hash),
            "candidate_steering_intent_hash":str(steering.intent_hash),
        },
        "compile_artifacts":artifact_bindings,
        "output_state":None,
        "replay_contract":{
            "audio_embedded":False,
            "midi_embedded":False,
            "non_destructive_replay_verify":True,
            "restore_is_explicit":True,
            "exact_audio_replay_claimed":False,
            "compile_determinism_only":True,
        },
    }
    # Checkpoint identity normalizes its own pin tag and path-dependent JSON raw hashes.
    cid=checkpoint_id_v61(body)
    pin_tag=f"checkpoint:{cid}"
    body["input_state"]["evidence"]["pin_tag"]=pin_tag
    evidence_store.pin_commit(evidence["commit_id"],pin_tag)
    payload={"checkpoint_id":cid,**body}
    out=Path(out_path) if out_path else Path(comp["midi_D"]).with_suffix(".performance_checkpoint.json")
    _atomic_write(out,(json.dumps(payload,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8"))
    return payload,out


def _policy_snapshot_from_file(path):
    mem=RepairPolicyMemoryV49(path)
    return policy_binding_v61(mem.snapshot())


def finalize_checkpoint_v61(checkpoint_path,evidence_store,policy_path,
                            decision_summary=None,artifacts=None,status="round_complete"):
    p=Path(checkpoint_path)
    cp=json.loads(p.read_text(encoding="utf-8"))
    if int(cp.get("schema",0))!=CHECKPOINT_SCHEMA:raise ValueError("unsupported_checkpoint_schema")
    output_evidence=_evidence_binding(evidence_store,evidence_store.head)
    output_policy=_policy_snapshot_from_file(policy_path)
    artifact_rows={}
    for name,path in (artifacts or {}).items():
        pp=Path(path)
        if pp.is_file():artifact_rows[str(name)]={"file_name":pp.name,**file_fingerprint_v61(pp)}
    decision=copy.deepcopy(decision_summary or {})
    result_body={
        "status":str(status),
        "evidence":output_evidence,
        "repair_policy":output_policy,
        "decision_summary":decision,
        "decision_sha256":_sha_bytes(_canonical(decision)),
        "artifacts":artifact_rows,
    }
    cp["output_state"]=result_body
    cp["result_binding_sha256"]=_sha_bytes(_canonical(result_body))
    _atomic_write(p,(json.dumps(cp,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8"))
    return cp


def load_checkpoint_v61(path):
    cp=json.loads(Path(path).read_text(encoding="utf-8"))
    if int(cp.get("schema",0))!=CHECKPOINT_SCHEMA:raise ValueError("unsupported_checkpoint_schema")
    clone=copy.deepcopy(cp);cid=clone.pop("checkpoint_id",None);clone.pop("result_binding_sha256",None)
    # checkpoint_id_v61 applies the path-independent immutable identity projection.
    expected=checkpoint_id_v61(clone)
    if cid!=expected:raise ValueError(f"checkpoint_id_mismatch:{cid}!={expected}")
    if cp.get("output_state") is not None:
        expected_result=_sha_bytes(_canonical(cp["output_state"]))
        actual_result=cp.get("result_binding_sha256")
        if actual_result!=expected_result:
            raise ValueError(f"checkpoint_result_binding_mismatch:{actual_result}!={expected_result}")
    return cp


def verify_checkpoint_v61(checkpoint_path,source_score,evidence_store,project_root=None,
                          current_policy_path=None,artifact_dir=None):
    cp=load_checkpoint_v61(checkpoint_path)
    source=Path(source_score).resolve()
    source_sha=_sha_bytes(source.read_bytes()) if source.exists() else None
    source_ok=source_sha==cp["source"]["sha256"]

    code_now=code_fingerprint_v61(project_root)
    code_ok=code_now["sha256"]==cp["compiler"]["sha256"]

    ev=cp["input_state"]["evidence"];commit_id=ev["commit_id"]
    commit=evidence_store._commit_by_id(commit_id)
    evidence_ok=bool(commit)
    evidence_details={}
    if commit:
        for name,row in ev["namespaces"].items():
            try:
                obj=evidence_store.read_commit_namespace(commit_id,name)
                actual=_sha_bytes(_canonical(obj))
                ok=actual==row["sha256"]
            except Exception as ex:
                actual=None;ok=False
                evidence_details[name]={"ok":False,"error":str(ex),"expected":row["sha256"]};continue
            evidence_details[name]={"ok":ok,"actual":actual,"expected":row["sha256"]}
            evidence_ok=evidence_ok and ok

    policy_current=None
    if current_policy_path is not None and Path(current_policy_path).exists():
        policy_current=_policy_snapshot_from_file(current_policy_path)
    policy_matches=(policy_current is not None and
                    policy_current["profile_hash"]==cp["input_state"]["repair_policy"]["profile_hash"] and
                    policy_current["generation"]==cp["input_state"]["repair_policy"]["generation"])

    artifact_checks={}
    base=Path(artifact_dir) if artifact_dir else Path(checkpoint_path).parent
    artifact_ok=True
    for key,row in cp["compile_artifacts"].items():
        p=base/row["file_name"]
        if not p.exists():
            artifact_checks[key]={"ok":False,"status":"missing","file":str(p)}
            artifact_ok=False;continue
        cur=file_fingerprint_v61(p)
        ok=cur["normalized_sha256"]==row["normalized_sha256"]
        artifact_checks[key]={"ok":ok,"file":str(p),
                              "expected_normalized_sha256":row["normalized_sha256"],
                              "actual_normalized_sha256":cur["normalized_sha256"]}
        artifact_ok=artifact_ok and ok

    return {
        "checkpoint_id":cp["checkpoint_id"],
        "source_ok":source_ok,"compiler_code_ok":code_ok,
        "evidence_commit_ok":evidence_ok,"evidence":evidence_details,
        "current_policy_matches_input":policy_matches,
        "current_policy":policy_current,
        "compile_artifacts_ok":artifact_ok,"artifacts":artifact_checks,
        "replay_ready":bool(source_ok and code_ok and evidence_ok),
    }


def _write_policy_payload(path,payload):
    # Validate by round-tripping RepairPolicyMemoryV49 hash contract.
    if int(payload.get("version",0))!=1:raise ValueError("unsupported_policy_payload")
    if not all(k in payload.get("values",{}) for k in KEYS):raise ValueError("policy_keys_missing")
    expected=RepairPolicyMemoryV49._hash(payload)
    _atomic_write(Path(path),(json.dumps(payload,sort_keys=True,indent=2)+"\n").encode("utf-8"))
    loaded=RepairPolicyMemoryV49(path).snapshot()
    if loaded.profile_hash!=expected:raise ValueError("restored_policy_hash_mismatch")
    return loaded


def replay_verify_checkpoint_v61(checkpoint_path,source_score,evidence_store,project_root=None):
    """Non-destructive compile replay. Evidence is verified read-only; no global state is restored."""
    cp=load_checkpoint_v61(checkpoint_path)
    pre=verify_checkpoint_v61(checkpoint_path,source_score,evidence_store,project_root,
                              current_policy_path=None,artifact_dir=Path(checkpoint_path).parent)
    if not (pre["source_ok"] and pre["compiler_code_ok"] and pre["evidence_commit_ok"]):
        return {"passed":False,"reason":"checkpoint_prerequisite_failed","preflight":pre}

    from compile_musicxml_strings_v61 import compile_file
    with tempfile.TemporaryDirectory(prefix="sonicraft_v61_replay_") as td:
        td=Path(td)
        policy=td/"checkpoint_policy.json"
        _write_policy_payload(policy,cp["input_state"]["repair_policy"]["payload"])
        # Keep original D filename so filename-bearing JSON sidecars normalize identically.
        midi_name=cp["compile_artifacts"]["midi_D"]["file_name"]
        out=td/midi_name
        comp=compile_file(Path(source_score),out,policy,int(cp["round_index"]))
        current=_artifact_bindings(comp)
        rows={};passed=True
        for key,expected in cp["compile_artifacts"].items():
            actual=current[key]
            ok=actual["normalized_sha256"]==expected["normalized_sha256"]
            rows[key]={
                "ok":ok,
                "expected":expected["normalized_sha256"],
                "actual":actual["normalized_sha256"],
                "raw_equal":actual["raw_sha256"]==expected["raw_sha256"],
            }
            passed=passed and ok
        return {
            "passed":passed,
            "reason":"deterministic_compile_match" if passed else "compile_artifact_mismatch",
            "checkpoint_id":cp["checkpoint_id"],
            "evidence_commit_verified":True,
            "policy_profile_hash":cp["input_state"]["repair_policy"]["profile_hash"],
            "conductor_intent_hash_expected":cp["input_state"]["conductor_intent_hash"],
            "conductor_intent_hash_actual":str(comp["conductor_intent"].intent_hash),
            "artifacts":rows,
            "audio_replay_claimed":False,
        }


def restore_checkpoint_environment_v61(checkpoint_path,evidence_store,evidence_paths,policy_path,
                                       backup_policy=True):
    cp=load_checkpoint_v61(checkpoint_path)
    target=cp["input_state"]["evidence"]["commit_id"]
    if not evidence_store._commit_by_id(target):raise KeyError(f"checkpoint_evidence_commit_missing:{target}")

    policy_path=Path(policy_path)
    backup=None
    if backup_policy and policy_path.exists():
        backup=policy_path.with_name(policy_path.name+".pre_v61_restore.bak")
        _atomic_write(backup,policy_path.read_bytes())

    evidence_store.rollback(evidence_paths,target)
    snap=_write_policy_payload(policy_path,cp["input_state"]["repair_policy"]["payload"])
    return {
        "restored":True,
        "checkpoint_id":cp["checkpoint_id"],
        "evidence_commit":target,
        "policy_generation":snap.generation,
        "policy_profile_hash":snap.profile_hash,
        "policy_backup":str(backup) if backup else None,
    }


def release_checkpoint_pin_v61(checkpoint_path,evidence_store):
    cp=load_checkpoint_v61(checkpoint_path)
    ev=cp["input_state"]["evidence"]
    tag=str(ev.get("pin_tag") or f"checkpoint:{cp['checkpoint_id']}")
    out=evidence_store.unpin_commit(ev["commit_id"],tag)
    return {"released":bool(out.get("unpinned")),"checkpoint_id":cp["checkpoint_id"],
            "evidence_commit":ev["commit_id"],"pin_result":out}


def _paths_from_args(a):
    from evidence_store_v60 import namespace_paths_v60
    if not a.utility:raise SystemExit("--utility required")
    return namespace_paths_v60(a.utility)


def main(argv=None):
    ap=argparse.ArgumentParser(description="SONICRAFT v6.1 Reproducible Performance Checkpoint")
    ap.add_argument("command",choices=["verify","replay","restore","release"])
    ap.add_argument("checkpoint",type=Path)
    ap.add_argument("--score",type=Path)
    ap.add_argument("--store",type=Path,required=True)
    ap.add_argument("--utility",type=Path)
    ap.add_argument("--policy",type=Path)
    a=ap.parse_args(argv)
    store=UnifiedEvidenceStoreV60(a.store)
    if a.command=="verify":
        if not a.score:raise SystemExit("--score required")
        out=verify_checkpoint_v61(a.checkpoint,a.score,store,current_policy_path=a.policy)
    elif a.command=="replay":
        if not a.score:raise SystemExit("--score required")
        out=replay_verify_checkpoint_v61(a.checkpoint,a.score,store)
    elif a.command=="restore":
        if not a.policy:raise SystemExit("--policy required")
        paths=_paths_from_args(a)
        out=restore_checkpoint_environment_v61(a.checkpoint,store,paths,a.policy,True)
    elif a.command=="release":
        out=release_checkpoint_pin_v61(a.checkpoint,store)
    else:raise AssertionError(a.command)
    print(json.dumps(out,indent=2,ensure_ascii=False))
    return 0 if out.get("passed",out.get("restored",True)) else 3

if __name__=="__main__":raise SystemExit(main())
