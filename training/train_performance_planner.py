from __future__ import annotations

"""Train SONICRAFT's note-level symbolic Performance Planner.

The planner is intentionally separate from the audio renderer. It predicts advisory
performance controls; explicit score/MIDI/keyswitch/CC values remain authoritative.
"""

import argparse
import contextlib
import hashlib
import json
import os
import random
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from models.performance_planner import SymbolicPerformancePlanner
from performance_planner_contract import CONTINUOUS_TARGETS, FEATURE_NAMES, PLANNER_SCHEMA, PLANNER_VERSION
from training_control import DEFAULT_PAUSE_FILE, DEFAULT_STATUS_FILE, PauseController, clear_pause, write_status


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class PlannerDataset(Dataset):
    def __init__(self, index: Path, split: str):
        self.index = Path(index)
        rows = [json.loads(x) for x in self.index.read_text(encoding="utf-8").splitlines() if x.strip()]
        self.rows = [r for r in rows if str(r.get("split", "train")) == str(split)]
        if not self.rows:
            raise RuntimeError(f"no Performance Planner rows for split={split!r} in {index}")
        for row in self.rows:
            if int(row.get("schema_version", 0)) != PLANNER_SCHEMA:
                raise RuntimeError(f"unsupported planner dataset schema: {row.get('schema_version')}")
            if str(row.get("planner_version")) != PLANNER_VERSION:
                raise RuntimeError(f"planner dataset version mismatch: {row.get('planner_version')}")
            if bool(row.get("release_blocked")):
                raise RuntimeError(f"release-blocked planner row cannot train: {row.get('sample_id')}")

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int):
        row = self.rows[idx]
        path = Path(row["file"])
        with np.load(path, allow_pickle=False) as data:
            features = torch.from_numpy(np.asarray(data["features"], dtype=np.float32))
            articulation = torch.from_numpy(np.asarray(data["articulation"], dtype=np.int64))
            continuous = torch.from_numpy(np.asarray(data["continuous"], dtype=np.float32))
        if features.ndim != 2 or features.shape[1] != len(FEATURE_NAMES):
            raise RuntimeError(f"bad feature shape in {path}: {tuple(features.shape)}")
        if articulation.shape != (features.shape[0],):
            raise RuntimeError(f"bad articulation shape in {path}")
        if continuous.shape != (features.shape[0], len(CONTINUOUS_TARGETS)):
            raise RuntimeError(f"bad continuous shape in {path}: {tuple(continuous.shape)}")
        return features, articulation, continuous


def collate(batch):
    max_notes = max(x[0].shape[0] for x in batch)
    b = len(batch)
    features = torch.zeros(b, max_notes, len(FEATURE_NAMES), dtype=torch.float32)
    articulation = torch.full((b, max_notes), -100, dtype=torch.long)
    continuous = torch.zeros(b, max_notes, len(CONTINUOUS_TARGETS), dtype=torch.float32)
    padding = torch.ones(b, max_notes, dtype=torch.bool)
    for i, (feat, art, cont) in enumerate(batch):
        n = feat.shape[0]
        features[i, :n] = feat
        articulation[i, :n] = art
        continuous[i, :n] = cont
        padding[i, :n] = False
    return features, articulation, continuous, padding


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
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch_cpu"])
    if torch.cuda.is_available() and "torch_cuda" in state:
        torch.cuda.set_rng_state_all(state["torch_cuda"])


def batch_loss(model, batch, device: str):
    features, articulation, continuous, padding = batch
    features = features.to(device, non_blocking=True)
    articulation = articulation.to(device, non_blocking=True)
    continuous = continuous.to(device, non_blocking=True)
    padding = padding.to(device, non_blocking=True)
    out = model(features, padding)
    art_loss = nn.functional.cross_entropy(
        out["articulation_logits"].reshape(-1, out["articulation_logits"].shape[-1]),
        articulation.reshape(-1),
        ignore_index=-100,
    )
    valid = (~padding).unsqueeze(-1).to(out["continuous"].dtype)
    denom = valid.sum().clamp_min(1.0) * out["continuous"].shape[-1]
    cont_loss = (((out["continuous"] - continuous) ** 2) * valid).sum() / denom
    loss = art_loss + 2.0 * cont_loss
    with torch.no_grad():
        pred = out["articulation_logits"].argmax(-1)
        mask = articulation != -100
        acc = ((pred == articulation) & mask).sum().float() / mask.sum().clamp_min(1)
        mae = ((out["continuous"] - continuous).abs() * valid).sum() / denom
    return loss, art_loss.detach(), cont_loss.detach(), acc.detach(), mae.detach()


def main() -> int:
    ap = argparse.ArgumentParser(description="Train the SONICRAFT Symbolic Performance Planner.")
    ap.add_argument("--index", default="datasets/processed/performance_planner_cleanroom_v1/index.jsonl")
    ap.add_argument("--out", default="checkpoints/performance_planner_last.pt")
    ap.add_argument("--best-out", default="checkpoints/performance_planner_best.pt")
    ap.add_argument("--train-split", default="train")
    ap.add_argument("--val-split", default="val")
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--accum", type=int, default=1)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--d-model", type=int, default=128)
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--heads", type=int, default=4)
    ap.add_argument("--ff-mult", type=int, default=3)
    ap.add_argument("--dropout", type=float, default=.08)
    ap.add_argument("--max-notes", type=int, default=512)
    ap.add_argument("--seed", type=int, default=20260917)
    ap.add_argument("--resume")
    ap.add_argument("--pause-file", default=str(DEFAULT_PAUSE_FILE))
    ap.add_argument("--status-file", default=str(DEFAULT_STATUS_FILE))
    ap.add_argument("--status-every", type=int, default=5)
    a = ap.parse_args()
    if a.epochs < 1 or a.batch < 1 or a.accum < 1:
        raise SystemExit("epochs, batch and accum must be >= 1")

    random.seed(a.seed)
    np.random.seed(a.seed)
    torch.manual_seed(a.seed)
    index = Path(a.index)
    train_ds = PlannerDataset(index, a.train_split)
    try:
        val_ds = PlannerDataset(index, a.val_split)
    except RuntimeError:
        val_ds = None
        print(f"[WARN] no validation split {a.val_split!r}; best checkpoint uses train loss")

    train_dl = DataLoader(train_ds, batch_size=a.batch, shuffle=True, num_workers=0,
                          pin_memory=torch.cuda.is_available(), collate_fn=collate)
    val_dl = None if val_ds is None else DataLoader(val_ds, batch_size=a.batch, shuffle=False, num_workers=0,
                                                    pin_memory=torch.cuda.is_available(), collate_fn=collate)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    cfg = {
        "feature_dim": len(FEATURE_NAMES), "d_model": a.d_model, "layers": a.layers,
        "heads": a.heads, "ff_mult": a.ff_mult, "dropout": a.dropout, "max_notes": a.max_notes,
    }
    model = SymbolicPerformancePlanner(**cfg).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=.01, betas=(.9, .95))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, a.epochs), eta_min=a.lr * .08)
    start_epoch = 0
    target_epoch = int(a.epochs)
    global_step = 0
    best = float("inf")

    if a.resume:
        ck = torch.load(a.resume, map_location="cpu", weights_only=False)
        if ck.get("planner_version") != PLANNER_VERSION or ck.get("config") != cfg:
            raise RuntimeError("Performance Planner resume checkpoint architecture/version mismatch")
        model.load_state_dict(ck["model"])
        optimizer.load_state_dict(ck["optimizer"])
        scheduler.load_state_dict(ck["scheduler"])
        start_epoch = int(ck.get("epoch", 0))
        target_epoch = int(ck.get("target_epoch", start_epoch + a.epochs))
        global_step = int(ck.get("global_step", 0))
        best = float(ck.get("best_val", best))
        restore_rng(ck.get("rng_state"))
        print("resumed planner", a.resume, "epoch", start_epoch, "global_step", global_step)

    use_amp = device == "cuda" and torch.cuda.is_bf16_supported()
    ampctx = lambda: torch.autocast(device_type="cuda", dtype=torch.bfloat16) if use_amp else contextlib.nullcontext()
    pause = PauseController(a.pause_file)
    pause.install_signal_handlers()
    out_path = Path(a.out)
    best_path = Path(a.best_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    best_path.parent.mkdir(parents=True, exist_ok=True)
    source_sha = sha256_file(index)
    current_epoch = start_epoch
    current_batch = 0

    def publish(state: str, message: str) -> None:
        write_status({
            "state": state,
            "message": message,
            "job_type": "performance_planner",
            "pid": os.getpid(),
            "python_executable": sys.executable,
            "argv": list(sys.argv),
            "checkpoint": str(out_path.resolve()),
            "best_checkpoint": str(best_path.resolve()),
            "epoch": current_epoch,
            "target_epoch": target_epoch,
            "batch_in_epoch": current_batch,
            "batches_in_epoch": len(train_dl),
            "global_step": global_step,
            "device": device,
            "pause_file": str(Path(a.pause_file).resolve()),
        }, a.status_file)

    def checkpoint(completed_epoch: int, paused: bool, reason: str = "") -> dict:
        return {
            "schema_version": PLANNER_SCHEMA,
            "planner_version": PLANNER_VERSION,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "config": cfg,
            "feature_names": list(FEATURE_NAMES),
            "continuous_targets": list(CONTINUOUS_TARGETS),
            "source_index": str(index.resolve()),
            "source_index_sha256": source_sha,
            "training_origin": "modeled_bootstrap",
            "final_expression_anchor": False,
            "epoch": int(completed_epoch),
            "target_epoch": int(target_epoch),
            "global_step": int(global_step),
            "best_val": float(best),
            "rng_state": rng_state(),
            "pause_state": {"paused": bool(paused), "reason": str(reason), "batch_in_epoch": int(current_batch)},
        }

    def safe_pause(completed_epoch: int, reason: str) -> int:
        torch.save(checkpoint(completed_epoch, True, reason), out_path)
        pause.consume()
        publish("paused", f"Performance Planner safely paused ({reason}); checkpoint saved to {out_path}")
        print("[PAUSED] planner checkpoint saved:", out_path, flush=True)
        return 0

    publish("running", "Performance Planner training started; PAUSE is available.")
    if pause.requested():
        return safe_pause(start_epoch, pause.reason() or "pre_start_request")

    try:
        for epoch in range(start_epoch, target_epoch):
            current_epoch = epoch
            current_batch = 0
            model.train()
            optimizer.zero_grad(set_to_none=True)
            totals = np.zeros(5, dtype=np.float64)
            steps = 0
            pending_pause = False
            for bi, batch in enumerate(train_dl):
                current_batch = bi + 1
                with ampctx():
                    loss, art_loss, cont_loss, acc, mae = batch_loss(model, batch, device)
                    scaled = loss / a.accum
                scaled.backward()
                boundary = ((bi + 1) % a.accum == 0) or (bi + 1 == len(train_dl))
                if boundary:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    optimizer.step()
                    optimizer.zero_grad(set_to_none=True)
                    global_step += 1
                totals += np.asarray([float(loss.detach()), float(art_loss), float(cont_loss), float(acc), float(mae)])
                steps += 1
                if pause.requested():
                    pending_pause = True
                if boundary and global_step % max(1, a.status_every) == 0:
                    publish("pause_requested" if pending_pause else "running",
                            "Pause requested; waiting for optimizer boundary." if pending_pause else "Planner training is running.")
                if boundary and pending_pause:
                    return safe_pause(epoch, pause.reason() or "pause_request")

            scheduler.step()
            train_metrics = totals / max(1, steps)
            score = float(train_metrics[0])
            val_msg = ""
            if val_dl is not None:
                model.eval()
                vals = []
                with torch.no_grad():
                    for batch in val_dl:
                        with ampctx():
                            vloss, _, _, vacc, vmae = batch_loss(model, batch, device)
                        vals.append((float(vloss), float(vacc), float(vmae)))
                vm = np.asarray(vals, dtype=np.float64).mean(axis=0)
                score = float(vm[0])
                val_msg = f" val_loss={vm[0]:.5f} val_art_acc={vm[1]:.3f} val_ctrl_mae={vm[2]:.4f}"
            msg = (f"planner epoch {epoch+1:03d} loss={train_metrics[0]:.5f} art={train_metrics[1]:.5f} "
                   f"ctrl={train_metrics[2]:.5f} art_acc={train_metrics[3]:.3f} ctrl_mae={train_metrics[4]:.4f}" + val_msg)
            print(msg)
            is_best = score < best
            if is_best:
                best = score
            ck = checkpoint(epoch + 1, False)
            ck["best_val"] = float(best)
            torch.save(ck, out_path)
            if is_best:
                torch.save(ck, best_path)
            current_epoch = epoch + 1
            current_batch = 0
            publish("running", msg)
            if pause.requested():
                return safe_pause(epoch + 1, pause.reason() or "pause_request")

        clear_pause(a.pause_file)
        publish("completed", f"Performance Planner training completed at epoch {target_epoch}.")
        return 0
    except BaseException as exc:
        publish("error", f"Performance Planner stopped with {type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
