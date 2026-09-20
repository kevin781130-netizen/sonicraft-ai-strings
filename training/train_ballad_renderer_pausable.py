from __future__ import annotations

"""Pausable SONICRAFT renderer trainer.

This keeps the existing renderer data/model/loss contract from train_ballad_renderer,
but adds a safe pause boundary:
- PAUSE button / pause file / SIGINT / SIGTERM requests a pause.
- The request is honored after a complete optimizer step.
- A full resumable checkpoint is written before the process exits.
- Resume restarts the partially completed epoch; model/EMA/optimizer/scheduler/RNG
  states are restored, but the weighted sampler draws a fresh order for that epoch.
"""

import argparse
import copy
import json
import os
import random
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, WeightedRandomSampler
from accumulation import accumulation_window_size, is_optimizer_boundary

import train_ballad_renderer as base
from phrase_provenance import build_phrase_provenance
from promotion_binding import promotion_binding
from source_policy import validate_index
from string_source_mixer import coverage_audit, load_registry, mixture_audit
from training_control import DEFAULT_PAUSE_FILE, DEFAULT_STATUS_FILE, PauseController, clear_pause, write_status


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="SONICRAFT renderer training with safe PAUSE/RESUME.")
    ap.add_argument("--index", default="datasets/processed/ballad_dac/index.jsonl")
    ap.add_argument("--val-index")
    ap.add_argument("--out", default="checkpoints/ballad_renderer_last.pt")
    ap.add_argument("--best-out", default="checkpoints/ballad_renderer_best.pt")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--accum", type=int, default=1)
    ap.add_argument("--preset", choices=base.PRESETS, default="compact")
    ap.add_argument("--registry", default="training/dataset_registry.json")
    ap.add_argument("--resume")
    ap.add_argument("--lr", type=float, default=1.5e-4)
    ap.add_argument("--ema", type=float, default=.999)
    ap.add_argument("--vibrato-expert", default=None)
    ap.add_argument("--performance-experts", default=None)
    ap.add_argument("--expert-freeze-epochs", type=int, default=12)
    ap.add_argument("--cond-dropout", type=float, default=.08)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--latent-ch", type=int, default=0)
    ap.add_argument("--latent-hz", type=float, default=0.0)
    ap.add_argument("--codec-kind", default="auto")
    ap.add_argument("--codec-sample-rate", type=int, default=0)
    ap.add_argument("--real-ratio", type=float, default=.80)
    ap.add_argument("--modeled-ratio", type=float, default=.20)
    ap.add_argument("--modeled-flow-weight", type=float, default=.35,
                    help="Down-weight modeled latent endpoint/timbre loss while keeping modeled transition losses active.")
    ap.add_argument("--acoustic-promotion")
    ap.add_argument("--pause-file", default=str(DEFAULT_PAUSE_FILE))
    ap.add_argument("--status-file", default=str(DEFAULT_STATUS_FILE))
    ap.add_argument("--status-every", type=int, default=1,
                    help="Write a status heartbeat every N optimizer steps.")
    return ap


def rng_state() -> dict:
    state = {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.get_rng_state(),
    }
    if torch.cuda.is_available():
        state["torch_cuda"] = torch.cuda.get_rng_state_all()
    return state


def restore_rng(state: dict | None) -> None:
    if not state:
        return
    try:
        if "python" in state:
            random.setstate(state["python"])
        if "numpy" in state:
            np.random.set_state(state["numpy"])
        if "torch_cpu" in state:
            torch.set_rng_state(state["torch_cpu"])
        if torch.cuda.is_available() and "torch_cuda" in state:
            torch.cuda.set_rng_state_all(state["torch_cuda"])
    except Exception as exc:
        print("[WARN] could not fully restore RNG state:", exc, flush=True)


def main() -> int:
    a = build_parser().parse_args()
    if a.epochs < 1:
        raise SystemExit("--epochs must be >= 1")
    if a.accum < 1:
        raise SystemExit("--accum must be >= 1")
    if a.status_every < 1:
        raise SystemExit("--status-every must be >= 1")

    promotion_id, curriculum = promotion_binding(a.acoustic_promotion)
    random.seed(a.seed)
    np.random.seed(a.seed)
    torch.manual_seed(a.seed)

    validate_index(a.index, a.registry)
    if a.val_index:
        validate_index(a.val_index, a.registry)

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ds = base.Segments(a.index)
    phrase_provenance = build_phrase_provenance(ds.rows, a.index)
    if phrase_provenance.get("enabled"):
        print("phrase fine-tune provenance", json.dumps(phrase_provenance, sort_keys=True))

    inferred_ch, inferred_hz, inferred_kind, inferred_sr = base.infer_latent_geometry(ds)
    latent_ch = int(a.latent_ch or inferred_ch)
    latent_hz = float(a.latent_hz or inferred_hz)
    codec_kind = inferred_kind if str(a.codec_kind).lower() == "auto" else str(a.codec_kind)
    codec_sample_rate = int(a.codec_sample_rate or inferred_sr)
    if latent_ch != inferred_ch:
        raise RuntimeError(f"latent channel override {latent_ch} != dataset {inferred_ch}")

    registry = load_registry(a.registry)
    mix_w = base.source_weights(ds.rows, a.registry, a.real_ratio, a.modeled_ratio)
    print("renderer string mixture", json.dumps(mixture_audit(ds.rows, mix_w, registry), sort_keys=True))
    print("renderer coverage curriculum", json.dumps(coverage_audit(ds.rows, mix_w, registry), sort_keys=True))
    modeled_sources = {
        str(k).lower() for k, v in registry.items()
        if str(v.get("training_origin", "real")).lower() == "modeled"
    }

    sampler = WeightedRandomSampler(mix_w, max(len(ds), 128), replacement=True)
    dl = DataLoader(ds, batch_size=a.batch, sampler=sampler, num_workers=0,
                    pin_memory=torch.cuda.is_available(), collate_fn=base.collate)
    vdl = None
    if a.val_index:
        vds = base.Segments(a.val_index)
        vdl = DataLoader(vds, batch_size=a.batch, shuffle=False, num_workers=0, collate_fn=base.collate)

    cfg = dict(base.PRESETS[a.preset])
    m = base.BalladFlowRenderer(latent_ch=latent_ch, **cfg).to(dev)
    expert_loaded = False
    if a.vibrato_expert and Path(a.vibrato_expert).exists():
        eck = torch.load(a.vibrato_expert, map_location="cpu", weights_only=False)
        m.vibrato_physics.load_state_dict(eck["model"], strict=True)
        expert_loaded = True
        print("loaded supervised vibrato expert", a.vibrato_expert)
    elif a.vibrato_expert:
        print("[INFO] vibrato expert checkpoint not found; HQ will train its submodule end-to-end:", a.vibrato_expert)

    if a.performance_experts and Path(a.performance_experts).exists():
        eck = torch.load(a.performance_experts, map_location="cpu", weights_only=False)
        m.performance_experts.load_state_dict(eck["model"], strict=True)
        expert_loaded = True
        print("loaded supervised performance experts", a.performance_experts)
    elif a.performance_experts:
        print("[INFO] performance experts checkpoint not found; HQ will train its submodule end-to-end:", a.performance_experts)

    ema = copy.deepcopy(m).eval().requires_grad_(False)
    opt = torch.optim.AdamW(m.parameters(), a.lr, weight_decay=.01, betas=(.9, .95))
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, a.epochs), eta_min=a.lr * .08)

    start = 0
    best = float("inf")
    global_step = 0
    target_epoch = int(a.epochs)
    resumed_partial = False
    saved_rng = None

    if a.resume:
        ck = torch.load(a.resume, map_location="cpu", weights_only=False)
        saved = ck.get("config", {})
        if any(saved.get(k) != cfg[k] for k in cfg):
            raise RuntimeError("Resume checkpoint architecture mismatch.")
        if int(ck.get("latent_ch", latent_ch)) != latent_ch:
            raise RuntimeError("Resume checkpoint latent geometry mismatch.")
        phrase_provenance = build_phrase_provenance(ds.rows, a.index, ck.get("phrase_finetune_provenance"))
        m.load_state_dict(ck["model"])
        ema.load_state_dict(ck.get("ema", ck["model"]))
        if "optimizer" in ck:
            opt.load_state_dict(ck["optimizer"])
        if "scheduler" in ck:
            sched.load_state_dict(ck["scheduler"])
        start = int(ck.get("epoch", 0))
        best = float(ck.get("best_val", best))
        global_step = int(ck.get("global_step", 0))
        target_epoch = int(ck.get("target_epoch", start + a.epochs))
        resumed_partial = bool((ck.get("pause_state") or {}).get("paused"))
        saved_rng = ck.get("rng_state")
        print("resumed", a.resume, "at epoch", start, "global_step", global_step, "target_epoch", target_epoch)

    restore_rng(saved_rng)

    expert_modules = (m.vibrato_physics, m.performance_experts)
    def set_expert_trainable(flag: bool) -> None:
        for mod in expert_modules:
            for param in mod.parameters():
                param.requires_grad_(flag)

    freeze_until = max(0, int(a.expert_freeze_epochs))
    if expert_loaded and freeze_until > 0 and start < freeze_until:
        set_expert_trainable(False)
        print("freezing calibrated physical experts until epoch", freeze_until)
    else:
        set_expert_trainable(True)

    use_amp = dev == "cuda" and torch.cuda.is_bf16_supported()
    ampctx = lambda: torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=use_amp)
    print("renderer params", sum(p.numel() for p in m.parameters()), "device", dev, "segments", len(ds), cfg,
          "controls", m.CONTROL_DIMS, "bf16", use_amp, "codec", codec_kind, "latent", latent_ch, "@", latent_hz, "Hz")

    pause = PauseController(a.pause_file)
    pause.install_signal_handlers()
    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    best_path = Path(a.best_out)
    best_path.parent.mkdir(parents=True, exist_ok=True)

    current_epoch = start
    current_batch = 0
    total_batches = len(dl)

    def publish(state: str, message: str, *, epoch: int | None = None, batch: int | None = None) -> None:
        write_status({
            "state": state,
            "message": message,
            "pid": os.getpid(),
            "python_executable": sys.executable,
            "argv": list(sys.argv),
            "checkpoint": str(out_path.resolve()),
            "best_checkpoint": str(best_path.resolve()),
            "epoch": current_epoch if epoch is None else int(epoch),
            "target_epoch": target_epoch,
            "batch_in_epoch": current_batch if batch is None else int(batch),
            "batches_in_epoch": total_batches,
            "global_step": global_step,
            "device": dev,
            "preset": a.preset,
            "pause_file": str(Path(a.pause_file).resolve()),
            "resumed_partial_epoch": resumed_partial,
        }, a.status_file)

    def make_checkpoint(completed_epoch: int, *, paused: bool, reason: str = "", batch_in_epoch: int = 0) -> dict:
        return {
            "model": m.state_dict(),
            "ema": ema.state_dict(),
            "optimizer": opt.state_dict(),
            "scheduler": sched.state_dict(),
            "epoch": int(completed_epoch),
            "target_epoch": int(target_epoch),
            "global_step": int(global_step),
            "config": cfg,
            "preset": a.preset,
            "latent_ch": latent_ch,
            "latent_hz": latent_hz,
            "codec_kind": codec_kind,
            "codec_sample_rate": codec_sample_rate,
            "articulations": 12,
            "control_dims": m.CONTROL_DIMS,
            "source_index": a.index,
            "val_index": a.val_index,
            "best_val": best,
            "schema_version": 9,
            "vibrato_expert_seed": a.vibrato_expert,
            "performance_experts_seed": a.performance_experts,
            "training_mix": {"real": a.real_ratio, "modeled": a.modeled_ratio,
                             "modeled_flow_weight": a.modeled_flow_weight, "curriculum": curriculum},
            "phrase_finetune_provenance": phrase_provenance,
            "acoustic_promotion_id": promotion_id,
            "rng_state": rng_state(),
            "pause_state": {
                "paused": bool(paused),
                "reason": str(reason),
                "batch_in_epoch": int(batch_in_epoch),
                "resume_restarts_partial_epoch": bool(paused and batch_in_epoch > 0),
            },
        }

    def safe_pause(completed_epoch: int, batch_in_epoch: int, reason: str) -> int:
        ck = make_checkpoint(completed_epoch, paused=True, reason=reason, batch_in_epoch=batch_in_epoch)
        torch.save(ck, out_path)
        pause.consume()
        publish("paused",
                f"Safe pause complete ({reason}). Checkpoint saved to {out_path}. RESUME will continue from this checkpoint. "
                "If paused mid-epoch, that epoch restarts with a fresh weighted sample order.",
                epoch=completed_epoch, batch=batch_in_epoch)
        print("[PAUSED] checkpoint saved:", out_path, flush=True)
        return 0

    publish("running", "Training started. PAUSE may be requested at any time.")
    if pause.requested():
        return safe_pause(start, 0, pause.reason() or "pre_start_request")

    try:
        for ep in range(start, target_epoch):
            current_epoch = ep
            current_batch = 0
            progress = ep / max(1, target_epoch - 1)
            sampler.weights = torch.as_tensor(
                base.source_weights(ds.rows, a.registry, a.real_ratio, a.modeled_ratio, progress=progress),
                dtype=torch.double)
            if expert_loaded and freeze_until > 0 and ep == freeze_until:
                set_expert_trainable(True)
                print("unfroze physical experts for end-to-end HQ refinement")

            m.train()
            opt.zero_grad(set_to_none=True)
            sums = {"flow": 0.0, "continuity": 0.0, "accel": 0.0, "modeled_fraction": 0.0}
            steps = 0
            pending_pause = False

            for bi, batch in enumerate(dl):
                current_batch = bi + 1
                window_size = accumulation_window_size(bi, total_batches, a.accum)
                with ampctx():
                    loss, met = base.run_batch(m, batch, dev, True, a.cond_dropout,
                                               modeled_sources, a.modeled_flow_weight)
                    loss = loss / window_size
                loss.backward()

                optimizer_boundary = is_optimizer_boundary(bi, total_batches, a.accum)
                if optimizer_boundary:
                    torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
                    opt.step()
                    opt.zero_grad(set_to_none=True)
                    base.ema_update(ema, m, a.ema)
                    global_step += 1

                for k, v in met.items():
                    sums[k] += float(v)
                steps += 1

                if pause.requested():
                    pending_pause = True

                if optimizer_boundary and (global_step % a.status_every == 0):
                    publish("pause_requested" if pending_pause else "running",
                            "Pause requested; waiting for safe checkpoint boundary." if pending_pause else "Training is running.")

                if optimizer_boundary and pending_pause:
                    return safe_pause(ep, bi + 1, pause.reason() or "pause_request")

            sched.step()
            denom = max(1, steps)
            msg = (f"epoch {ep+1:03d} train_flow={sums['flow']/denom:.6f} "
                   f"cont={sums['continuity']/denom:.6f} accel={sums['accel']/denom:.6f} "
                   f"modeled={sums['modeled_fraction']/denom:.3f} lr={sched.get_last_lr()[0]:.2e}")
            val = float("nan")
            if vdl:
                ema.eval()
                vals = []
                with torch.no_grad():
                    for batch in vdl:
                        with ampctx():
                            _, met = base.run_batch(ema, batch, dev, False, 0,
                                                    modeled_sources, a.modeled_flow_weight)
                        vals.append(float(met["flow"]))
                val = sum(vals) / max(1, len(vals))
                msg += f" val_flow={val:.6f}"
            print(msg)

            score = val if vdl else sums["flow"] / denom
            is_best = score < best
            if is_best:
                best = score

            ck = make_checkpoint(ep + 1, paused=False)
            torch.save(ck, out_path)
            if is_best:
                torch.save(ck, best_path)

            current_epoch = ep + 1
            current_batch = 0
            publish("running", msg, epoch=ep + 1, batch=0)

            if pause.requested():
                return safe_pause(ep + 1, 0, pause.reason() or "pause_request")

        clear_pause(a.pause_file)
        publish("completed", f"Training completed at epoch {target_epoch}. Final checkpoint: {out_path}",
                epoch=target_epoch, batch=0)
        return 0
    except BaseException as exc:
        publish("error", f"Training stopped with {type(exc).__name__}: {exc}",
                epoch=current_epoch, batch=current_batch)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
