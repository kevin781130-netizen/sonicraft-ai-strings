"""SONICRAFT v6.0 Unified Evidence Store / Memory Consolidation.

Transaction/governance layer for the five evidence memories introduced in v5.5-v5.9.

Namespaces remain logically independent:
- utility_v55
- audit_v56
- similarity_v57
- archetype_v58
- mixture_v59

The store does NOT blend their scores. It provides:
- content-addressed compressed snapshots
- atomic multi-namespace commits
- crash-drift detection and whole-set rollback
- per-namespace rollback
- structural privacy/contamination validation
- quarantine of invalid/drifted payloads
- export/import
- compact/deduplicate
- legacy JSON compatibility

No song identity, audio, MIDI, score text, note sequence, file name, or intent hash may exist
as structural fields inside an evidence namespace.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass,asdict
import argparse,base64,copy,hashlib,json,os,tempfile,zlib

STORE_VERSION=1
MAX_COMMITS=32
MAX_NAMESPACE_BYTES=2*1024*1024
NAMESPACES=("utility_v55","audit_v56","similarity_v57","archetype_v58","mixture_v59")
FORBIDDEN_STRUCTURAL_KEYS={
    "audio","audio_path","wav","midi","midi_path","score","score_text","source_score",
    "filename","file_name","song","song_title","track_title","note_sequence","notes",
    "intent_hash","user_id","identity",
}

def _canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def _sha(data):return hashlib.sha256(data).hexdigest()

def _atomic_write(path:Path,data:bytes):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=str(path.parent))
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        try:os.unlink(tmp)
        except FileNotFoundError:pass

def _walk_bad_keys(obj,path="$"):
    bad=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            ks=str(k).lower()
            if ks in FORBIDDEN_STRUCTURAL_KEYS:bad.append(f"{path}.{k}")
            bad.extend(_walk_bad_keys(v,f"{path}.{k}"))
    elif isinstance(obj,list):
        for i,v in enumerate(obj):bad.extend(_walk_bad_keys(v,f"{path}[{i}]"))
    return bad


def empty_namespace_payload_v60(name):
    privacy={
        "utility_v55":"aggregates only; no audio/MIDI/score text/file names",
        "audit_v56":"aggregate audit outcomes only; no audio/MIDI/score text/file names/identity",
        "similarity_v57":"aggregate transfer calibration only; no audio/MIDI/score text/file names/identity",
        "archetype_v58":"aggregate control/archetype render statistics only; no audio/MIDI/score text/file names/note sequences/intent hashes",
        "mixture_v59":"component-to-context aggregate calibration only; no audio/MIDI/score text/file names/note sequences/song identity/intent hashes",
    }[name]
    if name in ("utility_v55","audit_v56"):
        return {"version":1,"generation":0,"contexts":{},"privacy":privacy}
    if name=="similarity_v57":
        return {"version":1,"generation":0,"edges":{},"privacy":privacy}
    if name=="archetype_v58":
        return {"version":1,"generation":0,"contexts":{},"edges":{},"privacy":privacy}
    if name=="mixture_v59":
        return {"version":1,"generation":0,"edges":{},"privacy":privacy}
    raise KeyError(name)

def validate_namespace_payload_v60(name,obj):
    if name not in NAMESPACES:return False,[f"unknown_namespace:{name}"]
    if not isinstance(obj,dict):return False,["payload_not_object"]
    problems=[]
    if int(obj.get("version",0))!=1:problems.append("unsupported_legacy_version")
    gen=obj.get("generation",0)
    if not isinstance(gen,int) or gen<0:problems.append("invalid_generation")
    problems.extend("forbidden_structural_field:"+x for x in _walk_bad_keys(obj))
    if name in ("utility_v55","audit_v56") and not isinstance(obj.get("contexts",{}),dict):
        problems.append("contexts_not_object")
    if name=="similarity_v57" and not isinstance(obj.get("edges",{}),dict):
        problems.append("edges_not_object")
    if name=="archetype_v58":
        if not isinstance(obj.get("contexts",{}),dict):problems.append("contexts_not_object")
        if not isinstance(obj.get("edges",{}),dict):problems.append("edges_not_object")
    if name=="mixture_v59" and not isinstance(obj.get("edges",{}),dict):
        problems.append("edges_not_object")
    return not problems,problems

def _encode_blob(raw:bytes):
    return base64.b64encode(zlib.compress(raw,9)).decode("ascii")

def _decode_blob(text:str):
    return zlib.decompress(base64.b64decode(text.encode("ascii")))

@dataclass
class NamespaceStateV60:
    namespace:str
    generation:int
    sha256:str
    bytes:int

class UnifiedEvidenceStoreV60:
    def __init__(self,path):
        self.path=Path(path)
        self.generation=0
        self.head=None
        self.commits=[]
        self.blobs={}
        self.quarantine=[]
        self.pins={}
        self._load()

    def _empty(self):
        return {
            "version":STORE_VERSION,"generation":0,"head":None,"commits":[],
            "blobs":{},"quarantine":[],"pins":{},
            "privacy":"transaction metadata + compressed aggregate evidence only; no song identity/audio/MIDI/score text/note sequences/file names/intent hashes",
        }

    def _load(self):
        try:
            o=json.loads(self.path.read_text(encoding="utf-8"))
            if int(o.get("version",0))!=STORE_VERSION:return
            self.generation=max(0,int(o.get("generation",0)))
            self.head=o.get("head")
            self.commits=list(o.get("commits",[]))
            self.blobs=dict(o.get("blobs",{}))
            self.quarantine=list(o.get("quarantine",[]))
            self.pins={str(k):list(v) for k,v in dict(o.get("pins",{})).items()}
        except Exception:
            return

    def _payload(self):
        return {
            "version":STORE_VERSION,"generation":self.generation,"head":self.head,
            "commits":self.commits,"blobs":self.blobs,"quarantine":self.quarantine,"pins":self.pins,
            "privacy":"transaction metadata + compressed aggregate evidence only; no song identity/audio/MIDI/score text/note sequences/file names/intent hashes",
        }

    def _save(self):
        _atomic_write(self.path,(json.dumps(self._payload(),sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8"))

    def snapshot(self):return copy.deepcopy(self._payload())

    def _commit_by_id(self,cid):
        for c in self.commits:
            if c.get("id")==cid:return c
        return None

    def head_commit(self):
        return self._commit_by_id(self.head) if self.head else None

    def _put_valid_payload(self,name,obj):
        ok,problems=validate_namespace_payload_v60(name,obj)
        if not ok:raise ValueError(f"{name} invalid: {problems}")
        raw=_canonical(obj)
        if len(raw)>MAX_NAMESPACE_BYTES:raise ValueError(f"{name} too large:{len(raw)}")
        h=_sha(raw)
        if h not in self.blobs:self.blobs[h]=_encode_blob(raw)
        return NamespaceStateV60(name,int(obj.get("generation",0)),h,len(raw))

    def _read_blob_obj(self,h):
        if h not in self.blobs:raise KeyError(f"missing_blob:{h}")
        raw=_decode_blob(self.blobs[h])
        if _sha(raw)!=h:raise ValueError(f"blob_hash_mismatch:{h}")
        return json.loads(raw.decode("utf-8"))

    def read_commit_namespace(self,commit_id,name):
        c=self._commit_by_id(commit_id)
        if not c:raise KeyError(f"unknown_commit:{commit_id}")
        n=(c.get("namespaces") or {}).get(name)
        if not n:raise KeyError(f"commit_missing_namespace:{name}")
        return self._read_blob_obj(n["sha256"])

    def commit_payloads(self,payloads,reason="auto_loop_transaction"):
        missing=[n for n in NAMESPACES if n not in payloads]
        if missing:raise ValueError("missing_namespaces:"+",".join(missing))
        states={}
        for name in NAMESPACES:
            st=self._put_valid_payload(name,payloads[name])
            states[name]=asdict(st)
        parent=self.head
        body={"parent":parent,"namespaces":states,"reason":str(reason),"schema":1}
        cid=_sha(_canonical(body))[:24]
        if self._commit_by_id(cid):
            self.head=cid;self._save()
            return {"committed":False,"reason":"identical_transaction","commit_id":cid,"head":self.head}
        self.generation+=1
        commit={"id":cid,"store_generation":self.generation,**body}
        self.commits.append(commit);self.head=cid
        self.compact(MAX_COMMITS,save=False)
        self._save()
        return {"committed":True,"reason":str(reason),"commit_id":cid,"head":self.head,
                "store_generation":self.generation,"namespaces":states}

    def _load_legacy_payload(self,name,path):
        path=Path(path)
        raw=path.read_bytes()
        if len(raw)>MAX_NAMESPACE_BYTES:raise ValueError(f"{name}:legacy_too_large")
        obj=json.loads(raw.decode("utf-8"))
        ok,problems=validate_namespace_payload_v60(name,obj)
        if not ok:raise ValueError(f"{name}:invalid:{problems}")
        return obj

    def ensure_legacy_files(self,paths):
        created=[];repaired=[]
        for name in NAMESPACES:
            p=Path(paths[name])
            if not p.exists():
                obj=empty_namespace_payload_v60(name)
                _atomic_write(p,(json.dumps(obj,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8"))
                created.append(name)
                continue
            try:self._load_legacy_payload(name,p)
            except Exception:
                # On an uninitialized store there is no trusted head to restore from. Preserve the
                # bad bytes in quarantine, then initialize only that namespace to an empty v1 payload.
                if not self.head:
                    try:self.quarantine_bytes(name,p.read_bytes(),"bootstrap_invalid_legacy")
                    except Exception:pass
                    obj=empty_namespace_payload_v60(name)
                    _atomic_write(p,(json.dumps(obj,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8"))
                    repaired.append(name)
        if created or repaired:self._save()
        return {"created":created,"repaired":repaired}

    def capture_legacy(self,paths,reason="legacy_capture"):
        payloads={name:self._load_legacy_payload(name,paths[name]) for name in NAMESPACES}
        return self.commit_payloads(payloads,reason)

    def quarantine_bytes(self,name,raw,reason):
        raw=bytes(raw)
        h=_sha(raw)
        self.quarantine.append({
            "namespace":str(name),"sha256":h,"bytes":len(raw),"reason":str(reason),
            "store_generation":self.generation,
            "blob":_encode_blob(raw[:MAX_NAMESPACE_BYTES]),
        })
        self.quarantine=self.quarantine[-64:]

    def verify_legacy(self,paths):
        head=self.head_commit()
        rows={};all_match=bool(head)
        for name in NAMESPACES:
            path=Path(paths[name])
            expected=((head or {}).get("namespaces") or {}).get(name,{}).get("sha256")
            if not path.exists():
                rows[name]={"status":"missing","expected_sha256":expected};all_match=False;continue
            try:
                obj=self._load_legacy_payload(name,path)
                raw=_canonical(obj);actual=_sha(raw)
                status="match" if expected and actual==expected else ("valid_untracked" if not expected else "drift")
                if status!="match":all_match=False
                rows[name]={"status":status,"generation":int(obj.get("generation",0)),
                            "sha256":actual,"expected_sha256":expected}
            except Exception as ex:
                rows[name]={"status":"invalid","error":str(ex),"expected_sha256":expected};all_match=False
        return {"head":self.head,"all_match":all_match,"namespaces":rows}

    def restore_commit(self,commit_id,paths,namespaces=None):
        names=list(namespaces or NAMESPACES)
        c=self._commit_by_id(commit_id)
        if not c:raise KeyError(f"unknown_commit:{commit_id}")
        restored=[]
        for name in names:
            obj=self.read_commit_namespace(commit_id,name)
            ok,problems=validate_namespace_payload_v60(name,obj)
            if not ok:raise ValueError(f"stored_namespace_invalid:{name}:{problems}")
            _atomic_write(Path(paths[name]),(json.dumps(obj,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8"))
            restored.append(name)
        return {"restored":restored,"commit_id":commit_id}

    def bootstrap_or_recover(self,paths):
        ensured=self.ensure_legacy_files(paths)
        # First use: all five valid legacy memories become commit zero/one.
        if not self.head:
            return {"mode":"bootstrap","legacy_init":ensured,
                    "commit":self.capture_legacy(paths,"bootstrap_legacy_memories")}
        check=self.verify_legacy(paths)
        if check["all_match"]:return {"mode":"clean","head":self.head,"verification":check}
        # Any drift means the five-file set may be a partial transaction. Preserve every drifted
        # byte stream in quarantine, then restore the complete last head.
        for name,row in check["namespaces"].items():
            if row.get("status") in ("drift","invalid","valid_untracked"):
                p=Path(paths[name])
                if p.exists():
                    try:self.quarantine_bytes(name,p.read_bytes(),"startup_transaction_drift:"+row.get("status",""))
                    except Exception:pass
        self.restore_commit(self.head,paths)
        self._save()
        return {"mode":"recovered_to_head","head":self.head,"verification_before":check,
                "verification_after":self.verify_legacy(paths)}

    def rollback(self,paths,commit_id=None,namespaces=None):
        target=commit_id or self.head
        if not target:raise ValueError("no_commit_to_rollback")
        out=self.restore_commit(target,paths,namespaces)
        # Only a full rollback moves head. Namespace repair is a restore operation, not history rewrite.
        if not namespaces:
            self.head=target;self.generation+=1;self._save()
        return out

    def pin_commit(self,commit_id,tag):
        cid=str(commit_id);tag=str(tag)
        if not self._commit_by_id(cid):raise KeyError(f"cannot_pin_missing_commit:{cid}")
        tags=list(self.pins.get(cid,[]))
        if tag not in tags:tags.append(tag)
        self.pins[cid]=sorted(set(tags));self.generation+=1;self._save()
        return {"pinned":True,"commit_id":cid,"tags":list(self.pins[cid])}

    def unpin_commit(self,commit_id,tag=None):
        cid=str(commit_id)
        if cid not in self.pins:return {"unpinned":False,"reason":"commit_not_pinned","commit_id":cid}
        if tag is None:
            removed=list(self.pins.pop(cid,[]))
        else:
            tag=str(tag);tags=[x for x in self.pins.get(cid,[]) if x!=tag]
            removed=[tag] if len(tags)!=len(self.pins.get(cid,[])) else []
            if tags:self.pins[cid]=tags
            else:self.pins.pop(cid,None)
        self.generation+=1;self._save()
        return {"unpinned":bool(removed),"commit_id":cid,"removed":removed,
                "remaining":list(self.pins.get(cid,[]))}

    def pinned_commits(self):
        return {cid:list(tags) for cid,tags in self.pins.items() if tags}

    def compact(self,retain=MAX_COMMITS,save=True):
        retain=max(2,int(retain))
        all_commits=list(self.commits)
        recent_ids={c["id"] for c in all_commits[-retain:]}
        keep_ids=set(recent_ids)|set(self.pinned_commits())
        if self.head:keep_ids.add(self.head)
        self.commits=[c for c in all_commits if c.get("id") in keep_ids]
        # Drop stale pin records only if a commit was already missing before compaction.
        live_ids={c["id"] for c in self.commits}
        self.pins={cid:tags for cid,tags in self.pins.items() if cid in live_ids and tags}
        referenced=set()
        for c in self.commits:
            for row in (c.get("namespaces") or {}).values():
                if row.get("sha256"):referenced.add(row["sha256"])
        before=len(self.blobs)
        self.blobs={h:b for h,b in self.blobs.items() if h in referenced}
        if save:self._save()
        return {"commits":len(self.commits),"blobs_before":before,"blobs_after":len(self.blobs),
                "deduplicated_removed":before-len(self.blobs),
                "pinned_commits":len(self.pinned_commits())}

    def export_bundle(self,out_path):
        # Export is path-independent: it contains no machine-specific legacy paths.
        out=Path(out_path)
        _atomic_write(out,(json.dumps(self._payload(),sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8"))
        return {"exported":str(out),"sha256":_sha(out.read_bytes()),"head":self.head,
                "commits":len(self.commits),"blobs":len(self.blobs)}

    def import_bundle(self,in_path):
        o=json.loads(Path(in_path).read_text(encoding="utf-8"))
        if int(o.get("version",0))!=STORE_VERSION:raise ValueError("unsupported_store_version")
        # Validate every referenced blob before replacing current state.
        tmp=UnifiedEvidenceStoreV60(Path(str(self.path)+".import_probe"))
        tmp.generation=max(0,int(o.get("generation",0)));tmp.head=o.get("head")
        tmp.commits=list(o.get("commits",[]));tmp.blobs=dict(o.get("blobs",{}));tmp.quarantine=list(o.get("quarantine",[]))
        tmp.pins={str(k):list(v) for k,v in dict(o.get("pins",{})).items()}
        for c in tmp.commits:
            for name,row in (c.get("namespaces") or {}).items():
                if name not in NAMESPACES:raise ValueError("unknown_namespace_in_import")
                obj=tmp._read_blob_obj(row["sha256"])
                ok,problems=validate_namespace_payload_v60(name,obj)
                if not ok:raise ValueError(f"invalid_import_namespace:{name}:{problems}")
        if tmp.head and not tmp._commit_by_id(tmp.head):raise ValueError("import_head_missing")
        for cid,tags in tmp.pins.items():
            if tags and not tmp._commit_by_id(cid):raise ValueError(f"import_pin_commit_missing:{cid}")
        self.generation=tmp.generation;self.head=tmp.head;self.commits=tmp.commits
        self.blobs=tmp.blobs;self.quarantine=tmp.quarantine;self.pins=tmp.pins;self._save()
        return {"imported":True,"head":self.head,"commits":len(self.commits),"blobs":len(self.blobs)}

    def status(self):
        hc=self.head_commit()
        return {
            "version":STORE_VERSION,"store_generation":self.generation,"head":self.head,
            "commits":len(self.commits),"blobs":len(self.blobs),"quarantine":len(self.quarantine),
            "pinned_commits":len(self.pinned_commits()),"pins":self.pinned_commits(),
            "head_namespaces":copy.deepcopy((hc or {}).get("namespaces",{})),
        }

def namespace_paths_v60(utility_path):
    from counterfactual_auditor_v56 import default_audit_path_v56
    from context_similarity_transfer_v57 import default_transfer_path_v57
    from performance_archetype_memory_v58 import default_archetype_path_v58
    from archetype_mixture_v59 import default_mixture_path_v59
    u=Path(utility_path)
    return {
        "utility_v55":u,
        "audit_v56":Path(default_audit_path_v56(u)),
        "similarity_v57":Path(default_transfer_path_v57(u)),
        "archetype_v58":Path(default_archetype_path_v58(u)),
        "mixture_v59":Path(default_mixture_path_v59(u)),
    }

def default_evidence_store_path_v60(utility_path):
    p=Path(utility_path)
    return p.with_name(p.stem+".unified_evidence_store_v60.json")

def main(argv=None):
    ap=argparse.ArgumentParser(description="SONICRAFT v6.0 Unified Evidence Store manager")
    ap.add_argument("command",choices=["status","verify","compact","export","rollback"])
    ap.add_argument("--store",type=Path,required=True)
    ap.add_argument("--utility",type=Path,default=None,help="legacy v5.5 Utility path; derives the other four paths")
    ap.add_argument("--out",type=Path,default=None)
    ap.add_argument("--commit",default=None)
    ap.add_argument("--retain",type=int,default=MAX_COMMITS)
    a=ap.parse_args(argv)
    st=UnifiedEvidenceStoreV60(a.store)
    if a.command=="status":out=st.status()
    elif a.command=="compact":out=st.compact(a.retain)
    elif a.command=="export":
        if not a.out:raise SystemExit("--out required")
        out=st.export_bundle(a.out)
    else:
        if not a.utility:raise SystemExit("--utility required")
        paths=namespace_paths_v60(a.utility)
        if a.command=="verify":out=st.verify_legacy(paths)
        elif a.command=="rollback":out=st.rollback(paths,a.commit)
        else:raise AssertionError(a.command)
    print(json.dumps(out,indent=2,ensure_ascii=False))
    return 0

if __name__=="__main__":raise SystemExit(main())
