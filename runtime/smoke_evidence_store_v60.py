from pathlib import Path
import tempfile,json,copy
from evidence_store_v60 import UnifiedEvidenceStoreV60,NAMESPACES,empty_namespace_payload_v60

def write(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,sort_keys=True,indent=2)+"\n",encoding="utf-8")

with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    paths={n:td/(n+".json") for n in NAMESPACES}
    store=UnifiedEvidenceStoreV60(td/"store.json")

    # First run creates five empty compatible legacy memories and captures one transaction.
    boot=store.bootstrap_or_recover(paths)
    assert boot["mode"]=="bootstrap",boot
    assert all(paths[n].exists() for n in NAMESPACES)
    assert store.head and len(store.commits)==1
    head0=store.head
    blobs0=len(store.blobs)
    assert blobs0<=5

    # Transaction 2 changes only utility + audit; unchanged namespace blobs must deduplicate.
    u=json.loads(paths["utility_v55"].read_text());u["generation"]=1
    u["contexts"]={"build|transition":{"total_windows":1.0,"slots":{"B":{"evidence":1.0,"utility":.8,"wins":1.0,"overall":.82,"safety":.9}}}}
    write(paths["utility_v55"],u)
    a=json.loads(paths["audit_v56"].read_text());a["generation"]=1
    a["contexts"]={"build|transition":{"prune_opportunities":2,"audits":0,"false_prunes":0,"near_misses":0,"recent":[],"disabled":False,"disabled_reason":"","clean_streak":0,"mean_counterfactual_gain":0.0,"max_counterfactual_gain":0.0}}
    write(paths["audit_v56"],a)
    c2=store.capture_legacy(paths,"round_1")
    assert c2["committed"],c2
    head1=store.head
    assert head1!=head0
    assert len(store.blobs)<=blobs0+2,(blobs0,len(store.blobs))

    # Partial/crashed write: mutate only utility after committed head.
    drift=json.loads(paths["utility_v55"].read_text());drift["generation"]=99
    drift["contexts"]["corrupt_partial"]={"total_windows":99,"slots":{}}
    write(paths["utility_v55"],drift)
    check=store.verify_legacy(paths)
    assert not check["all_match"] and check["namespaces"]["utility_v55"]["status"]=="drift",check
    rec=store.bootstrap_or_recover(paths)
    assert rec["mode"]=="recovered_to_head",rec
    restored=json.loads(paths["utility_v55"].read_text())
    assert restored["generation"]==1 and "corrupt_partial" not in restored["contexts"]
    assert store.quarantine and store.quarantine[-1]["namespace"]=="utility_v55"

    # Structural contamination must never become a commit.
    bad=json.loads(paths["utility_v55"].read_text());bad["audio"]="forbidden"
    write(paths["utility_v55"],bad)
    try:
        store.capture_legacy(paths,"bad")
        raise AssertionError("contamination accepted")
    except Exception as ex:
        assert "forbidden_structural_field" in str(ex),ex
    store.rollback(paths,head1)
    assert store.verify_legacy(paths)["all_match"]

    # New clean commit and full rollback.
    m=json.loads(paths["mixture_v59"].read_text());m["generation"]=2
    m["edges"]={"intimate->build|transition":{"trust":.8}}
    write(paths["mixture_v59"],m)
    c3=store.capture_legacy(paths,"round_2")
    head2=store.head
    assert c3["committed"] and head2!=head1
    store.rollback(paths,head1)
    assert store.head==head1
    assert json.loads(paths["mixture_v59"].read_text())["generation"]==0

    # Export/import is path independent and integrity checked.
    bundle=td/"export.json"
    ex=store.export_bundle(bundle)
    clone=UnifiedEvidenceStoreV60(td/"clone.json")
    im=clone.import_bundle(bundle)
    assert im["head"]==store.head
    assert clone.status()["head_namespaces"]==store.status()["head_namespaces"]

    # Compact/dedup keeps current rollback target valid.
    comp=store.compact(retain=2)
    assert comp["commits"]<=2
    assert store.read_commit_namespace(store.head,"utility_v55")["generation"]==1

    print("SONICRAFT v6.0 unified evidence store transaction/rollback/quarantine/export smoke OK",
          "head",store.head,"commits",len(store.commits),"blobs",len(store.blobs),
          "quarantine",len(store.quarantine),"dedup_removed",comp["deduplicated_removed"])
