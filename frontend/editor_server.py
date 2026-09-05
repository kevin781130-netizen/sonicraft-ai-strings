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
                "version": "6.4.0",
                "platform": sys.platform,
                "windows_runtime": os.name == "nt",
                "compile_bat": resolve_bat("COMPILE_MUSICXML_STRINGS_v62.bat").exists(),
                "auto_loop_bat": resolve_bat("AUTO_LOOP_STRINGS_v62.bat").exists(),
                "root": str(ROOT),
                "logs": str(LOGS),
            })
            return
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
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
