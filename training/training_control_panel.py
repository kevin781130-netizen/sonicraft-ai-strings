from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from training_control import DEFAULT_PAUSE_FILE, DEFAULT_STATUS_FILE, clear_pause, read_status, request_pause, resume_last

HOST = "127.0.0.1"

HTML = r"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SONICRAFT Training Control</title>
<style>
:root{color-scheme:dark;--bg:#090d12;--panel:#141b24;--line:#344253;--text:#f3f5f7;--muted:#94a2b3;--red:#d96c6c;--green:#75c99a;--gold:#d7ad63}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:linear-gradient(180deg,#090d12,#0d131b);font-family:Inter,"Segoe UI",sans-serif;color:var(--text);display:grid;place-items:center;padding:24px}
.wrap{width:min(760px,100%)}h1{font-size:24px;margin:0 0 6px;letter-spacing:.04em}.sub{color:var(--muted);margin-bottom:18px;line-height:1.5}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 16px 50px #0007}
.state{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:16px}.badge{padding:7px 11px;border:1px solid var(--line);border-radius:999px;font-weight:800;font-size:12px}.badge.running{color:var(--green);border-color:#35634b}.badge.paused{color:var(--gold);border-color:#725c33}.badge.pause_requested{color:#ffcb7b;border-color:#805c2b}.badge.error{color:#ff9b9b;border-color:#7b4141}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin:14px 0}.m{background:#101720;border:1px solid #293746;border-radius:9px;padding:10px}.m small{display:block;color:var(--muted);font-size:10px}.m strong{display:block;margin-top:5px;font-size:14px;overflow-wrap:anywhere}
.actions{display:grid;grid-template-columns:2fr 1.2fr 1fr;gap:10px;margin-top:16px}button{border:1px solid var(--line);border-radius:10px;background:#18222e;color:var(--text);padding:14px 12px;font-weight:800;cursor:pointer}button:hover{border-color:#60738a}.pause{background:#542626;border-color:#8d4545;color:#ffd1d1}.resume{background:#183a2a;border-color:#35664b;color:#c8f2d8}.clear{color:#c6d0db}
.msg{margin-top:14px;min-height:44px;padding:10px 12px;border-radius:9px;background:#101720;border:1px solid #293746;color:var(--muted);white-space:pre-wrap;line-height:1.45}
.note{margin-top:14px;color:var(--muted);font-size:12px;line-height:1.55}.note b{color:#dce4ed}
@media(max-width:600px){.actions,.grid{grid-template-columns:1fr}.state{align-items:flex-start;flex-direction:column}}
</style>
</head>
<body><div class="wrap">
<h1>SONICRAFT TRAINING CONTROL</h1>
<div class="sub">安全暫停不是硬殺程序：先完成目前 optimizer step，存完整 checkpoint，再正常退出。</div>
<div class="card">
  <div class="state"><div><b>訓練狀態</b><div id="updated" class="sub" style="margin:5px 0 0"></div></div><span id="badge" class="badge">LOADING</span></div>
  <div class="grid">
    <div class="m"><small>Epoch</small><strong id="epoch">—</strong></div>
    <div class="m"><small>Global step</small><strong id="step">—</strong></div>
    <div class="m"><small>Checkpoint</small><strong id="ckpt">—</strong></div>
    <div class="m"><small>Process</small><strong id="pid">—</strong></div>
  </div>
  <div class="actions">
    <button id="pause" class="pause">⏸ PAUSE TRAINING</button>
    <button id="resume" class="resume">▶ RESUME TRAINING</button>
    <button id="clear" class="clear">CLEAR REQUEST</button>
  </div>
  <div id="msg" class="msg">Loading…</div>
  <div class="note"><b>PAUSE</b> 可隨時按；trainer 會在最近的安全 optimizer boundary 存檔。<br>
  <b>RESUME</b> 只在狀態為 PAUSED 時啟用，會重開原本的訓練命令並載入剛存的 checkpoint。<br>
  關掉這個網頁不會影響正在跑的訓練。</div>
</div></div>
<script>
const $=s=>document.querySelector(s);
async function api(path, method='GET'){
  const r=await fetch(path,{method,headers:{'Cache-Control':'no-store'}});
  const j=await r.json();
  if(!r.ok) throw new Error(j.message||('HTTP '+r.status));
  return j;
}
function text(v,f='—'){return v===undefined||v===null||v===''?f:String(v)}
async function refresh(){
  try{
    const j=await api('/api/status');
    const state=j.pause_requested && j.state==='running'?'pause_requested':(j.state||'idle');
    const b=$('#badge'); b.textContent=state.toUpperCase(); b.className='badge '+state;
    $('#epoch').textContent=text(j.epoch)+(j.target_epoch!=null?' / '+j.target_epoch:'');
    $('#step').textContent=text(j.global_step);
    $('#ckpt').textContent=text(j.checkpoint);
    $('#pid').textContent=j.pid?('PID '+j.pid+' · '+text(j.device)):text(j.device);
    $('#msg').textContent=text(j.message,'Ready.');
    $('#updated').textContent=j.updated_at_unix?'Last update '+new Date(j.updated_at_unix*1000).toLocaleString():'No trainer heartbeat yet';
    $('#resume').disabled=j.state!=='paused';
  }catch(e){$('#msg').textContent='Status error: '+e.message}
}
$('#pause').onclick=async()=>{try{const j=await api('/api/pause','POST');$('#msg').textContent=j.message;await refresh()}catch(e){$('#msg').textContent='Pause failed: '+e.message}};
$('#resume').onclick=async()=>{try{const j=await api('/api/resume','POST');$('#msg').textContent=j.message;setTimeout(refresh,400)}catch(e){$('#msg').textContent='Resume failed: '+e.message}};
$('#clear').onclick=async()=>{try{const j=await api('/api/clear','POST');$('#msg').textContent=j.message;await refresh()}catch(e){$('#msg').textContent='Clear failed: '+e.message}};
refresh(); setInterval(refresh,1500);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "SONICRAFTTrainingControl/1.0"

    def log_message(self, fmt, *args):
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)

    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            raw = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if path == "/api/status":
            self._json(200, read_status(getattr(self.server, "status_file", None)))
            return
        self._json(404, {"ok": False, "message": "Unknown endpoint"})

    def do_POST(self):
        path = urlparse(self.path).path
        pause_file = getattr(self.server, "pause_file", None)
        status_file = getattr(self.server, "status_file", None)
        if path == "/api/pause":
            target = request_pause(pause_file, source="training_control_panel")
            self._json(200, {
                "ok": True,
                "message": f"Pause requested. Safe checkpoint will be written at the next optimizer boundary.\n{target}",
            })
            return
        if path == "/api/clear":
            existed = clear_pause(pause_file)
            self._json(200, {"ok": True, "message": "Pause request cleared." if existed else "No pause request was present."})
            return
        if path == "/api/resume":
            try:
                proc = resume_last(status_file)
            except Exception as exc:
                self._json(409, {"ok": False, "message": str(exc)})
                return
            self._json(200, {"ok": True, "pid": proc.pid, "message": f"Training resumed as PID {proc.pid}."})
            return
        self._json(404, {"ok": False, "message": "Unknown endpoint"})


def main() -> int:
    ap = argparse.ArgumentParser(description="Local SONICRAFT training pause/resume panel.")
    ap.add_argument("--port", type=int, default=0, help="0 chooses a free localhost port")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--pause-file", default=str(DEFAULT_PAUSE_FILE))
    ap.add_argument("--status-file", default=str(DEFAULT_STATUS_FILE))
    args = ap.parse_args()

    httpd = ThreadingHTTPServer((HOST, args.port), Handler)
    httpd.pause_file = str(Path(args.pause_file).resolve())
    httpd.status_file = str(Path(args.status_file).resolve())
    httpd.verbose = args.verbose
    port = int(httpd.server_address[1])
    url = f"http://{HOST}:{port}/"
    print(f"SONICRAFT Training Control: {url}")
    print("Close this window only when you no longer need the control panel.")
    if args.open:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
