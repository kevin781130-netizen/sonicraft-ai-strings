#!/usr/bin/env python3
"""SONICRAFT AI Strings Q4 v6.4 local editor server.

Dependency-free, local-only product frontend. It never listens outside 127.0.0.1.
The browser editor owns visual/project editing; compile and Auto-Loop are delegated
back to the existing v6.2 runtime BATs on Windows so this layer does not fork the
performance/compiler truth.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = Path(__file__).resolve().parent
CACHE = FRONTEND / "cache"
LOGS = ROOT / "logs" / "frontend_v64"
CACHE.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)
PART_NAMES = ["Vln I", "Vln II", "Viola", "Cello"]
STEP_NAMES = ["C", "C", "D", "D", "E", "F", "F", "G", "G", "A", "A", "B"]
ALTER = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]


def pitch_xml(midi: int) -> str:
    midi = max(0, min(127, int(midi)))
    pc = midi % 12
    octv = midi // 12 - 1
    alt = f"<alter>{ALTER[pc]}</alter>" if ALTER[pc] else ""
    return f"<pitch><step>{STEP_NAMES[pc]}</step>{alt}<octave>{octv}</octave></pitch>"


def articulation_xml(name: str) -> str:
    n = (name or "Sustain").strip().lower()
    if n == "legato":
        return '<notations><slur type="start" number="1"/></notations>'
    if n == "portamento":
        return '<notations><slide type="start" number="1"/></notations>'
    if n in ("staccato", "spiccato"):
        return '<notations><articulations><staccato/></articulations></notations>'
    if n == "marcato":
        return '<notations><articulations><strong-accent/></articulations></notations>'
    if n == "tremolo":
        return '<notations><ornaments><tremolo type="single">3</tremolo></ornaments></notations>'
    if n == "trill":
        return '<notations><ornaments><trill-mark/></ornaments></notations>'
    if n == "harmonic":
        return '<notations><technical><harmonic/></technical></notations>'
    return ""


def project_to_musicxml(project: dict, target: Path) -> Path:
    """Create a parser-friendly MusicXML bridge from the editor project.

    We intentionally keep the bridge small and deterministic. All notes live in one
    long measure per string part; the SONICRAFT parser uses absolute cursor movement,
    so <forward>/<backup> retains overlapping/polyphonic note positions without adding
    another notation engine dependency.
    """
    notes = project.get("notes") or []
    tempo = float(project.get("tempo") or 120.0)
    divisions = 480
    by_part = [[] for _ in PART_NAMES]
    for raw in notes:
        try:
            part = max(0, min(3, int(raw.get("track", 0))))
            start = max(0.0, float(raw.get("start", 0.0)))
            dur = max(1 / 16, float(raw.get("duration", 1.0)))
            pitch = max(0, min(127, int(raw.get("pitch", 60))))
            vel = max(1, min(127, int(raw.get("velocity", 82))))
            dyn = max(1, min(127, int(raw.get("dynamics", vel))))
            by_part[part].append((start, dur, pitch, vel, dyn, str(raw.get("articulation", "Sustain"))))
        except Exception:
            continue

    part_list = ''.join(
        f'<score-part id="P{i+1}"><part-name>{escape(name)}</part-name></score-part>'
        for i, name in enumerate(PART_NAMES)
    )
    parts = []
    for idx, entries in enumerate(by_part):
        entries.sort(key=lambda x: (x[0], x[2], x[1]))
        cursor = 0
        body = [
            '<measure number="1">',
            f'<attributes><divisions>{divisions}</divisions><key><fifths>0</fifths></key>'
            '<time><beats>4</beats><beat-type>4</beat-type></time></attributes>',
        ]
        if idx == 0:
            body.append(f'<direction placement="above"><sound tempo="{tempo:.6g}"/></direction>')
        for start, dur, pitch, vel, dyn, art in entries:
            s = int(round(start * divisions))
            d = max(1, int(round(dur * divisions)))
            delta = s - cursor
            if delta > 0:
                body.append(f'<forward><duration>{delta}</duration></forward>')
                cursor += delta
            elif delta < 0:
                body.append(f'<backup><duration>{-delta}</duration></backup>')
                cursor += delta
            # Dynamic direction is deliberately note-local so the existing parser picks it up.
            dyn_mark = 'mf'
            if dyn < 32: dyn_mark = 'ppp'
            elif dyn < 45: dyn_mark = 'pp'
            elif dyn < 58: dyn_mark = 'p'
            elif dyn < 72: dyn_mark = 'mp'
            elif dyn < 90: dyn_mark = 'mf'
            elif dyn < 104: dyn_mark = 'f'
            elif dyn < 116: dyn_mark = 'ff'
            else: dyn_mark = 'fff'
            body.append(f'<direction><direction-type><dynamics><{dyn_mark}/></dynamics></direction-type></direction>')
            if art.lower() == 'pizzicato':
                body.append('<direction><direction-type><words>pizz.</words></direction-type><sound pizzicato="yes"/></direction>')
            elif art.lower() == 'flautando':
                body.append('<direction><direction-type><words>flautando</words></direction-type></direction>')
            else:
                body.append('<direction><direction-type><words>arco</words></direction-type><sound pizzicato="no"/></direction>')
            notation = articulation_xml(art)
            body.append(
                '<note>' + pitch_xml(pitch) + f'<duration>{d}</duration><voice>1</voice>'
                f'<velocity>{vel}</velocity>{notation}</note>'
            )
            cursor += d
        body.append('</measure>')
        parts.append(f'<part id="P{idx+1}">' + ''.join(body) + '</part>')

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<score-partwise version="3.1">'
        f'<part-list>{part_list}</part-list>' + ''.join(parts) + '</score-partwise>'
    )
    target.write_text(xml, encoding="utf-8")
    return target


def resolve_bat(bat_name: str) -> Path:
    for candidate in (ROOT / bat_name, ROOT / "Tools" / bat_name):
        if candidate.exists():
            return candidate
    return ROOT / bat_name



DNNI_JOB_LOCK = threading.Lock()
DNNI_JOB = {
    "id": None,
    "action": None,
    "stage": None,
    "state": "idle",
    "started_at": None,
    "finished_at": None,
    "returncode": None,
    "message": "",
    "log": None,
}


def training_python() -> str:
    candidates = [
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "bin" / "python",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return sys.executable


def _job_snapshot() -> dict:
    with DNNI_JOB_LOCK:
        return dict(DNNI_JOB)


def _set_job(**kwargs):
    with DNNI_JOB_LOCK:
        DNNI_JOB.update(kwargs)


def _job_log_path(action: str, job_id: str) -> Path:
    d = ROOT / "logs" / "frontend_v64" / "dnni_jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{time.strftime('%Y%m%d_%H%M%S')}_{action}_{job_id[:8]}.log"


def _write_log_header(log, action: str, commands: list[list[str]]):
    log.write(f"ACTION: {action}\n")
    log.write(f"START: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    for i, cmd in enumerate(commands, 1):
        log.write(f"COMMAND {i}: {' '.join(map(str, cmd))}\n")
    log.write("\n")
    log.flush()


def _run_dnni_job(job_id: str, action: str, commands: list[list[str]], stage: str | None = None):
    snap = _job_snapshot()
    log_path = Path(snap["log"]) if snap.get("id") == job_id and snap.get("log") else _job_log_path(action, job_id)
    rc = 0
    message = ""
    try:
        with log_path.open("a", encoding="utf-8", errors="replace") as log:
            _write_log_header(log, action, commands)
            for idx, cmd in enumerate(commands, 1):
                _set_job(message=f"{action}: command {idx}/{len(commands)}")
                creationflags = 0
                if os.name == "nt" and action == "train":
                    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(ROOT),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                    creationflags=creationflags,
                    env={**os.environ, "SONICRAFT_NONINTERACTIVE": "1"},
                )
                rc = proc.wait()
                if rc != 0:
                    message = f"{action} stopped with exit code {rc}"
                    break
            if rc == 0:
                message = f"{action} completed"
            log.write(f"\nEND: {time.strftime('%Y-%m-%d %H:%M:%S')} rc={rc}\n")
    except Exception as exc:
        rc = -1
        message = f"{type(exc).__name__}: {exc}"
        try:
            log_path.write_text(message + "\n", encoding="utf-8", errors="replace")
        except Exception:
            pass
    _set_job(
        state="completed" if rc == 0 else "failed",
        finished_at=time.time(),
        returncode=rc,
        message=message,
    )


def _setup_commands() -> list[list[str]]:
    if os.name != "nt":
        raise RuntimeError("RTX 5090 environment setup is Windows-only.")
    vpy = ROOT / ".venv" / "Scripts" / "python.exe"
    return [
        ["py", "-3.11", "-m", "venv", str(ROOT / ".venv")],
        [str(vpy), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
        [str(vpy), "-m", "pip", "install", "--upgrade", "torch==2.11.0", "torchaudio==2.11.0", "--index-url", "https://download.pytorch.org/whl/cu130"],
        [str(vpy), "-m", "pip", "install", "-r", str(ROOT / "training" / "requirements.txt"), "--upgrade-strategy", "only-if-needed"],
        [str(vpy), str(ROOT / "training" / "scripts" / "dnni_5090_preflight.py")],
    ]


def _dnni_commands(action: str, stage: str | None = None) -> list[list[str]]:
    py = training_python()
    if action == "setup":
        return _setup_commands()
    if action == "import":
        return [[py, str(ROOT / "training" / "scripts" / "import_dnni_input_dir.py")]]
    if action == "prepare":
        return [
            [py, str(ROOT / "training" / "scripts" / "generate_dnni_capture_plan.py")],
            [py, str(ROOT / "training" / "scripts" / "generate_dnni_batch_capture_midi.py")],
        ]
    if action == "slice":
        return [
            [py, str(ROOT / "training" / "scripts" / "slice_dnni_batch_bounces.py")],
            [py, str(ROOT / "training" / "scripts" / "build_dnni_render_manifest.py")],
            [py, str(ROOT / "training" / "scripts" / "dnni_pipeline_fingerprint.py")],
        ]
    if action == "train":
        if os.name != "nt":
            raise RuntimeError("RTX 5090 BAT training is Windows-only.")
        return [["cmd.exe", "/d", "/s", "/c", "call", str(ROOT / "scripts" / "TRAIN_DNNI_FOUR_TIMBRES_5090_RESEARCH.bat")]]
    if action == "verify":
        return [[py, str(ROOT / "training" / "scripts" / "dnni_training_finalize.py"), "--verify"]]
    if action == "reset-stage":
        if stage not in ("codec", "renderer", "distill", "shortcut"):
            raise ValueError("Invalid reset stage.")
        return [[py, str(ROOT / "training" / "scripts" / "archive_dnni_training_state.py"), "--from-stage", stage, "--include-logs"]]
    raise ValueError(f"Unsupported DNNI action: {action}")


def start_dnni_job(action: str, stage: str | None = None) -> dict:
    if action not in ("setup", "import", "prepare", "slice", "train", "verify", "reset-stage"):
        raise ValueError("Action is not allowed.")
    with DNNI_JOB_LOCK:
        if DNNI_JOB.get("state") == "running":
            raise RuntimeError(f"Another DNNI action is already running: {DNNI_JOB.get('action')}")
        job_id = uuid.uuid4().hex
        log_path = _job_log_path(action, job_id)
        DNNI_JOB.update({
            "id": job_id,
            "action": action,
            "stage": stage,
            "state": "running",
            "started_at": time.time(),
            "finished_at": None,
            "returncode": None,
            "message": f"{action} starting",
            "log": str(log_path),
        })
    commands = _dnni_commands(action, stage)
    thread = threading.Thread(target=_run_dnni_job, args=(job_id, action, commands, stage), daemon=True)
    thread.start()
    return _job_snapshot()


def request_dnni_stop() -> dict:
    stop = ROOT / "checkpoints" / "dnni4_stop_after_epoch.flag"
    stop.parent.mkdir(parents=True, exist_ok=True)
    stop.write_text("stop\n", encoding="utf-8")
    return {"ok": True, "message": "Safe stop requested. The trainer will checkpoint after the current batch/optimizer step.", "path": str(stop)}


def dnni_status() -> dict:
    py = training_python()
    script = ROOT / "training" / "scripts" / "dnni_training_status.py"
    if not script.exists():
        return {"ok": False, "message": "DNNI training status tool is missing."}
    try:
        proc = subprocess.run(
            [py, str(script), "--json"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
        )
        if not proc.stdout.strip():
            return {"ok": False, "message": proc.stderr[-4000:] or f"status exited {proc.returncode}"}
        data = json.loads(proc.stdout)
        data["ok"] = proc.returncode in (0, 2)
        data["status_exit_code"] = proc.returncode
        if proc.stderr.strip():
            data["stderr_tail"] = proc.stderr[-2000:]
        return data
    except Exception as exc:
        return {"ok": False, "message": f"{type(exc).__name__}: {exc}"}


def dnni_log_tail(limit: int = 12000) -> dict:
    snap = _job_snapshot()
    p = Path(snap["log"]) if snap.get("log") else None
    text = ""
    if p and p.exists():
        try:
            text = p.read_text(encoding="utf-8", errors="replace")[-max(1000, min(limit, 100000)):]
        except Exception as exc:
            text = f"{type(exc).__name__}: {exc}"
    return {"ok": True, "job": snap, "text": text}



def run_bat(bat_name: str, project: dict) -> dict:
    if os.name != "nt":
        return {
            "ok": False,
            "code": "WINDOWS_RUNTIME_REQUIRED",
            "message": "The editor is functional here, but SONICRAFT BAT execution is Windows-only. Use this same package on Windows for Compile/Auto-Loop.",
        }
    bat = resolve_bat(bat_name)
    if not bat.exists():
        return {"ok": False, "code": "BAT_MISSING", "message": f"Missing {bat.name}"}
    stamp = time.strftime("%Y%m%d_%H%M%S")
    src = project_to_musicxml(project, CACHE / f"editor_{stamp}.musicxml")
    log = LOGS / f"{Path(bat_name).stem}_{stamp}.log"
    cmd = ["cmd.exe", "/d", "/s", "/c", f'"{bat}" "{src}"']
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, errors="replace")
    payload = (
        f"COMMAND: {' '.join(cmd)}\nEXIT: {proc.returncode}\n\nSTDOUT\n{proc.stdout}\n\nSTDERR\n{proc.stderr}\n"
    )
    log.write_text(payload, encoding="utf-8", errors="replace")
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "source": str(src),
        "log": str(log),
        "stdout_tail": proc.stdout[-6000:],
        "stderr_tail": proc.stderr[-3000:],
    }


class Handler(SimpleHTTPRequestHandler):
    server_version = "SONICRAFTEditor/6.4"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND), **kwargs)

    def log_message(self, fmt, *args):
        # Keep browser traffic quiet unless the user intentionally starts DEBUG_EDITOR_V64.bat.
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)

    def _json(self, status: int, obj: dict):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self._json(200, {
                "ok": True,
                "version": "7.0.0",
                "platform": sys.platform,
                "windows_runtime": os.name == "nt",
                "compile_bat": resolve_bat("COMPILE_MUSICXML_STRINGS_v62.bat").exists(),
                "auto_loop_bat": resolve_bat("AUTO_LOOP_STRINGS_v62.bat").exists(),
                "dnni_training": (ROOT / "training" / "scripts" / "dnni_training_status.py").exists(),
                "root": str(ROOT),
                "logs": str(LOGS),
            })
            return
        if parsed.path == "/api/dnni/status":
            self._json(200, dnni_status())
            return
        if parsed.path == "/api/dnni/job":
            self._json(200, {"ok": True, "job": _job_snapshot()})
            return
        if parsed.path == "/api/dnni/log":
            self._json(200, dnni_log_tail())
            return
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/dnni/stop":
            self._json(200, request_dnni_stop())
            return
        if parsed.path == "/api/dnni/action":
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 100_000)
                payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                action = str(payload.get("action") or "")
                stage = payload.get("stage")
                job = start_dnni_job(action, str(stage) if stage else None)
                self._json(202, {"ok": True, "job": job})
            except ValueError as exc:
                self._json(400, {"ok": False, "message": str(exc)})
            except RuntimeError as exc:
                self._json(409, {"ok": False, "message": str(exc)})
            except Exception as exc:
                self._json(500, {"ok": False, "message": f"{type(exc).__name__}: {exc}"})
            return
        if parsed.path not in ("/api/compile", "/api/auto-loop", "/api/export-musicxml"):
            self._json(404, {"ok": False, "message": "Unknown endpoint"})
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 10_000_000)
            project = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:
            self._json(400, {"ok": False, "message": f"Invalid project JSON: {exc}"})
            return
        if parsed.path == "/api/export-musicxml":
            stamp = time.strftime("%Y%m%d_%H%M%S")
            target = project_to_musicxml(project, CACHE / f"export_{stamp}.musicxml")
            self._json(200, {"ok": True, "path": str(target), "xml": target.read_text(encoding="utf-8")})
            return
        bat = "COMPILE_MUSICXML_STRINGS_v62.bat" if parsed.path == "/api/compile" else "AUTO_LOOP_STRINGS_v62.bat"
        self._json(200, run_bat(bat, project))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0, help="0 chooses a free localhost port")
    ap.add_argument("--open", action="store_true", help="open the editor in the default browser")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        sample = {"tempo": 50, "notes": [{"track": 0, "start": 0, "duration": 1, "pitch": 69, "velocity": 82, "dynamics": 70, "articulation": "Legato"}]}
        out = project_to_musicxml(sample, CACHE / "_smoke.musicxml")
        ok = out.exists() and "Vln I" in out.read_text(encoding="utf-8")
        out.unlink(missing_ok=True)
        print(json.dumps({"ok": ok, "frontend": str(FRONTEND), "version": "6.4.0"}))
        return 0 if ok else 1

    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    httpd.verbose = args.verbose
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/index.html"
    print(f"SONICRAFT Editor v6.4: {url}")
    print(f"Logs: {LOGS}")
    if args.open:
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
