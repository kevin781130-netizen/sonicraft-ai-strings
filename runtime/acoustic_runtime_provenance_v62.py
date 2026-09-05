"""SONICRAFT v6.2 Acoustic Runtime Provenance / Model Environment Binding.

Dependency-light, fail-explanatory runtime provenance capture.

Design inputs intentionally align with open provenance ecosystems without making SONICRAFT depend
on them at runtime:
- in-toto Statement v1 / SLSA provenance vocabulary for subject + resolved dependencies;
- CycloneDX ML-BOM concepts for model/framework transparency;
- ONNX Runtime and PyTorch native introspection APIs for the actually selected inference backend.

The binding does NOT claim bit-identical audio. It records enough immutable acoustic execution
context to explain why a later render may differ: model bytes/manifest, renderer code, selected
backend, framework/build, device capability, sample rate and render controls.
"""
from __future__ import annotations

from pathlib import Path
import copy, hashlib, importlib.metadata, json, os, platform, subprocess, sys

PROVENANCE_SCHEMA = 1
PROVENANCE_VERSION = "6.2"

# Code that can directly alter acoustic rendering or backend selection.  The combined renderer
# build SHA is deliberately independent from file paths.
RENDERER_CODE_FILES = (
    "runtime/renderer_service.py",
    "runtime/model_backend.py",
    "runtime/ort_model_backend.py",
    "runtime/runtime_backend_selector_v24.py",
    "runtime/release_integrity.py",
    "runtime/flow_sampler.py",
    "runtime/control_builder_np.py",
    "runtime/stage_renderer.py",
    "runtime/stage_renderer_np.py",
    "runtime/string_physical_runtime_v42.py",
    "runtime/string_ensemble_runtime_v44.py",
    "runtime/string_gesture_runtime_v45.py",
    "runtime/string_transition_runtime_v46.py",
    "runtime/string_phrase_runtime_v47.py",
    "runtime/portable_rng_v27.py",
    "runtime/protocol.py",
)

# Only variables capable of changing runtime selection / kernels / numerical behavior are bound.
ENV_KEYS = (
    "SONICRAFT_RUNTIME",
    "SONICRAFT_DEVICE",
    "SONICRAFT_ORT_DIR",
    "SONICRAFT_NATIVE_PROMOTION",
    "SONICRAFT_NATIVE_FOOTPRINT",
    "SONICRAFT_ALLOW_UNVERIFIED_MODELS",
    "CUDA_VISIBLE_DEVICES",
    "CUDA_MODULE_LOADING",
    "CUBLAS_WORKSPACE_CONFIG",
    "NVIDIA_TF32_OVERRIDE",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
)


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path, chunk: int = 4 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _package_version(name: str):
    try:
        return importlib.metadata.version(name)
    except Exception:
        return None


def _run_text(cmd, timeout=3.0):
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           text=True, timeout=float(timeout), check=False)
        text = (p.stdout or "").strip()
        return text if p.returncode == 0 and text else None
    except Exception:
        return None


def _root(project_root=None) -> Path:
    return Path(project_root or Path(__file__).resolve().parents[1]).resolve()


def _installed_home_like_renderer(project_root=None) -> Path:
    """Mirror renderer_service's install-home decision closely enough for provenance capture."""
    root = _root(project_root)
    if (root / "install-location.json").exists():
        return root
    env_home = os.getenv("SONICRAFT_AI_STRINGS_HOME", "").strip()
    if env_home:
        return Path(env_home).resolve()
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA", str(Path.home())))
        return (base / "SONICRAFT" / "AI Strings Q4").resolve()
    # Source/dev environments do not have Windows LOCALAPPDATA semantics.  Keep the source root so
    # model absence is recorded explicitly rather than fingerprinting a fabricated user path.
    return root


def resolve_model_dir_v62(model_dir=None, project_root=None) -> Path:
    if model_dir:
        return Path(model_dir).expanduser().resolve()
    return _installed_home_like_renderer(project_root) / "Models"


def _code_binding(project_root=None):
    root = _root(project_root)
    files = {}
    missing = []
    for rel in RENDERER_CODE_FILES:
        p = root / rel
        if p.is_file():
            files[rel] = _sha_file(p)
        else:
            missing.append(rel)
    return {
        "sha256": _sha_bytes(_canonical(files)),
        "files": files,
        "missing": missing,
    }


def _manifest_rows(model_dir: Path):
    """Capture model-pack bytes without inventing a package manager dependency.

    For release_model_manifest.json, every declared file is re-hashed when present.  This makes the
    v6.2 checkpoint authoritative even if a manifest was edited or files were replaced afterward.
    ORT export files receive the same treatment via export_manifest.json plus known renderer/decoder
    candidates.
    """
    model_dir = Path(model_dir)
    out = {
        "present": model_dir.is_dir(),
        "release_manifest": None,
        "files": [],
        "ort": {"manifest": None, "files": []},
    }
    mp = model_dir / "release_model_manifest.json"
    if mp.is_file():
        raw = mp.read_bytes()
        row = {"sha256": _sha_bytes(raw), "bytes": len(raw), "parse_ok": False}
        try:
            m = json.loads(raw.decode("utf-8")); row["parse_ok"] = True
            row["schema"] = int(m.get("schema", 0)); row["profile"] = m.get("profile")
            row["version"] = m.get("version"); row["product"] = m.get("product")
            row["release_approved"] = bool(m.get("release_approved", False))
            row["commercial_safe"] = bool(m.get("commercial_safe", False))
            for e in (m.get("files") or []):
                name = str(e.get("name") or "")
                if not name or "/" in name or "\\" in name:
                    continue
                p = model_dir / name
                expected = str(e.get("sha256") or "").lower()
                r = {"name": name, "role": str(e.get("role") or ""), "expected_sha256": expected,
                     "present": p.is_file()}
                if p.is_file():
                    r["bytes"] = p.stat().st_size
                    r["actual_sha256"] = _sha_file(p)
                    r["hash_match"] = len(expected) == 64 and r["actual_sha256"].lower() == expected
                out["files"].append(r)
        except Exception as ex:
            row["parse_error"] = f"{type(ex).__name__}: {ex}"
        out["release_manifest"] = row

    ort_dir = Path(os.getenv("SONICRAFT_ORT_DIR", "").strip() or (model_dir / "ORT"))
    op = ort_dir / "export_manifest.json"
    if op.is_file():
        raw = op.read_bytes(); om = None
        row = {"sha256": _sha_bytes(raw), "bytes": len(raw), "parse_ok": False}
        try:
            om = json.loads(raw.decode("utf-8")); row["parse_ok"] = True
            for k in ("schema", "version", "sampling_family", "codec_sample_rate", "latent_ch", "latent_hz"):
                if k in om: row[k] = om[k]
        except Exception as ex:
            row["parse_error"] = f"{type(ex).__name__}: {ex}"
        out["ort"]["manifest"] = row
        candidates = []
        if isinstance(om, dict):
            for key, default in (("renderer", "renderer_frontier.onnx"), ("decoder", "strings_vae64_decoder.onnx")):
                raw_name = str(om.get(key, default)); candidates.append(Path(raw_name).name)
        candidates += ["renderer_frontier.onnx", "renderer_frontier.ort",
                       "strings_vae64_decoder.onnx", "strings_vae64_decoder.ort"]
        seen = set()
        for name in candidates:
            if name in seen: continue
            seen.add(name); p = ort_dir / name
            if p.is_file():
                out["ort"]["files"].append({"name": name, "bytes": p.stat().st_size,
                                             "sha256": _sha_file(p)})
    return out


def _nvidia_driver_row():
    text = _run_text(["nvidia-smi", "--query-gpu=driver_version,name,compute_cap,memory.total", "--format=csv,noheader,nounits"])
    if not text:
        return None
    rows = []
    for line in text.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) >= 4:
            rows.append({"driver_version": parts[0], "name": parts[1],
                         "compute_capability": parts[2], "memory_mib": parts[3]})
        else:
            rows.append({"raw": line.strip()})
    return rows


def _torch_runtime_row():
    try:
        import torch
    except Exception as ex:
        return {"available": False, "package_version": _package_version("torch"),
                "import_error": f"{type(ex).__name__}: {ex}"}
    row = {
        "available": True,
        "version": str(getattr(torch, "__version__", "unknown")),
        "cuda_build": str(getattr(getattr(torch, "version", None), "cuda", None)),
        "hip_build": str(getattr(getattr(torch, "version", None), "hip", None)),
        "cuda_available": bool(torch.cuda.is_available()),
    }
    try: row["cudnn_version"] = torch.backends.cudnn.version()
    except Exception: row["cudnn_version"] = None
    try:
        row["flags"] = {
            "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
            "cudnn_deterministic": bool(torch.backends.cudnn.deterministic),
            "cudnn_allow_tf32": bool(getattr(torch.backends.cudnn, "allow_tf32", False)),
            "matmul_allow_tf32": bool(getattr(torch.backends.cuda.matmul, "allow_tf32", False)),
            "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
        }
    except Exception:
        pass
    devices = []
    if row["cuda_available"]:
        try:
            for i in range(int(torch.cuda.device_count())):
                p = torch.cuda.get_device_properties(i)
                cap = torch.cuda.get_device_capability(i)
                devices.append({"index": i, "name": str(p.name),
                                "compute_capability": f"{int(cap[0])}.{int(cap[1])}",
                                "total_memory": int(p.total_memory),
                                "multi_processor_count": int(getattr(p, "multi_processor_count", 0))})
        except Exception as ex:
            row["device_probe_error"] = f"{type(ex).__name__}: {ex}"
    row["devices"] = devices
    return row


def _ort_runtime_row():
    try:
        import onnxruntime as ort
    except Exception as ex:
        return {"available": False,
                "package_version": _package_version("onnxruntime") or _package_version("onnxruntime-gpu"),
                "import_error": f"{type(ex).__name__}: {ex}"}
    row = {"available": True, "version": str(getattr(ort, "__version__", "unknown"))}
    for attr, key in (("get_device", "device"), ("get_build_info", "build_info"),
                      ("get_available_providers", "available_providers"), ("get_all_providers", "all_providers")):
        try: row[key] = getattr(ort, attr)()
        except Exception: row[key] = None
    return row


def _select_backend(project_root, model_dir, requested, mock):
    if mock:
        return "mock", "explicit mock"
    requested = str(requested or "auto").strip().lower()
    if requested not in ("auto", "torch", "ort"): requested = "auto"
    try:
        from runtime_backend_selector_v24 import select_backend
        return select_backend(_installed_home_like_renderer(project_root), Path(model_dir), requested)
    except Exception as ex:
        # Fail explanatory: record the selector failure.  Explicit requested backend is still known;
        # AUTO cannot safely pretend which backend will be used.
        if requested in ("torch", "ort"):
            return requested, f"selector_probe_failed:{type(ex).__name__}:{ex}"
        return "unknown", f"selector_probe_failed:{type(ex).__name__}:{ex}"


def _stable_model_identity(model_capture):
    """Drop path/error prose while retaining authoritative hashes/presence state."""
    q = copy.deepcopy(model_capture)
    # parse_error is forensic text that can vary by interpreter; parse_ok + hashes are enough.
    if isinstance(q.get("release_manifest"), dict): q["release_manifest"].pop("parse_error", None)
    if isinstance(q.get("ort", {}).get("manifest"), dict): q["ort"]["manifest"].pop("parse_error", None)
    return q


def capture_acoustic_runtime_provenance_v62(*, project_root=None, model_dir=None,
                                             backend="auto", mock=False,
                                             sample_rate=48000, chunk_seconds=40.0,
                                             overlap_seconds=.75, local_context=.85,
                                             max_local_context_seconds=28.0,
                                             renderer_settings=None):
    root = _root(project_root); model_root = resolve_model_dir_v62(model_dir, root)
    selected, selection_detail = _select_backend(root, model_root, backend, bool(mock))
    code = _code_binding(root); models = _manifest_rows(model_root)

    system = {
        "os": platform.system(), "os_release": platform.release(),
        "machine": platform.machine(), "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(), "python_cache_tag": getattr(sys.implementation, "cache_tag", None),
    }
    packages = {"numpy": _package_version("numpy")}
    backend_runtime = {"selected": selected}
    if selected == "torch":
        backend_runtime["torch"] = _torch_runtime_row()
    elif selected == "ort":
        backend_runtime["onnxruntime"] = _ort_runtime_row()
    elif selected == "mock":
        backend_runtime["mock_version"] = "engineering-only-v1"
    else:
        # Unknown AUTO selection: record both probes for diagnosis but the selected=unknown state
        # remains a hard provenance mismatch until a concrete backend can be resolved.
        backend_runtime["torch_probe"] = _torch_runtime_row()
        backend_runtime["onnxruntime_probe"] = _ort_runtime_row()

    nvidia = _nvidia_driver_row() if selected in ("torch", "ort", "unknown") else None
    env = {k: os.getenv(k) for k in ENV_KEYS if os.getenv(k) is not None}
    render = {
        "sample_rate": int(sample_rate),
        "chunk_seconds": round(float(chunk_seconds), 9),
        "overlap_seconds": round(float(overlap_seconds), 9),
        "local_context_seconds": round(float(local_context), 9),
        "max_local_context_seconds": round(float(max_local_context_seconds), 9),
    }
    for k, v in sorted((renderer_settings or {}).items()):
        if isinstance(v, (str, int, float, bool)) or v is None:
            render[str(k)] = v

    identity = {
        "schema": PROVENANCE_SCHEMA,
        "sonicraft_version": PROVENANCE_VERSION,
        "renderer_build": code,
        "model_environment": _stable_model_identity(models),
        "backend": {
            "requested": str(backend), "selected": selected,
            "runtime": backend_runtime,
        },
        "system": system,
        "nvidia": nvidia,
        "environment": env,
        "render_config": render,
    }
    binding = _sha_bytes(_canonical(identity))
    return {
        "schema": PROVENANCE_SCHEMA,
        "version": PROVENANCE_VERSION,
        "binding_sha256": binding,
        "identity": identity,
        "forensics": {
            "model_dir_display": str(model_root),
            "selection_detail": str(selection_detail),
            "python_executable_display": str(sys.executable),
            "packages_observed": packages,
            "bit_identical_audio_claimed": False,
        },
    }


def _diff(a, b, prefix=""):
    rows = []
    if type(a) is not type(b):
        return [{"path": prefix or "$", "expected": a, "actual": b}]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{prefix}.{k}" if prefix else str(k)
            if k not in a: rows.append({"path": p, "expected": "<absent>", "actual": b[k]})
            elif k not in b: rows.append({"path": p, "expected": a[k], "actual": "<absent>"})
            else: rows.extend(_diff(a[k], b[k], p))
        return rows
    if isinstance(a, list):
        if a != b: rows.append({"path": prefix or "$", "expected": a, "actual": b})
        return rows
    if a != b: rows.append({"path": prefix or "$", "expected": a, "actual": b})
    return rows


def verify_acoustic_runtime_provenance_v62(expected, **capture_kwargs):
    current = capture_acoustic_runtime_provenance_v62(**capture_kwargs)
    ok = str(expected.get("binding_sha256")) == current["binding_sha256"]
    return {
        "ok": ok,
        "expected_binding_sha256": expected.get("binding_sha256"),
        "actual_binding_sha256": current["binding_sha256"],
        "differences": [] if ok else _diff(expected.get("identity"), current.get("identity"))[:128],
        "current": current,
    }


def export_in_toto_slsa_envelope_v62(provenance, subject_name="sonicraft-acoustic-runtime"):
    """Unsigned local in-toto Statement / SLSA-shaped export.

    This is an interoperability envelope, not a claim that a remote trusted SLSA builder signed it.
    """
    identity = provenance["identity"]
    deps = []
    rm = identity.get("model_environment", {}).get("release_manifest")
    if isinstance(rm, dict) and rm.get("sha256"):
        deps.append({"uri": "model-pack:release_model_manifest.json",
                     "digest": {"sha256": rm["sha256"]}})
    for row in identity.get("model_environment", {}).get("files", []):
        sha = row.get("actual_sha256") or row.get("expected_sha256")
        if sha:
            deps.append({"uri": "model:" + str(row.get("name")), "digest": {"sha256": sha}})
    for row in identity.get("model_environment", {}).get("ort", {}).get("files", []):
        if row.get("sha256"):
            deps.append({"uri": "ort-model:" + str(row.get("name")), "digest": {"sha256": row["sha256"]}})
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": str(subject_name), "digest": {"sha256": provenance["binding_sha256"]}}],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://sonicraft.local/acoustic-runtime-binding/v1",
                "externalParameters": {"renderConfig": identity.get("render_config", {})},
                "internalParameters": {"backend": identity.get("backend", {}), "system": identity.get("system", {})},
                "resolvedDependencies": deps,
            },
            "runDetails": {
                "builder": {"id": "https://sonicraft.local/runtime-provenance/v6.2",
                            "version": {"sonicraft": PROVENANCE_VERSION}},
                "metadata": {},
                "byproducts": [{"name": "renderer-build",
                                "digest": {"sha256": identity.get("renderer_build", {}).get("sha256", "")}}],
            },
        },
        "sonicraft": {"unsigned_local_attestation": True, "bit_identical_audio_claimed": False},
    }
