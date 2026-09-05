@echo off
setlocal
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 echo [INFO] No .venv activated; using current Python.
set IDX=datasets\processed\ballad_dac\index.jsonl
set TR=datasets\processed\ballad_dac\train.jsonl
set VA=datasets\processed\ballad_dac\val.jsonl
set VIBARG=
set PERFARG=

python training\scripts\check_release_sources.py --index "%IDX%" --registry training\dataset_registry.json || exit /b 1
python training\scripts\split_by_group.py --index "%IDX%" --train "%TR%" --val "%VA%" --val-percent 8 || exit /b 1
python training\evaluate_controls.py --index "%TR%" --out reports\control_coverage_v07.json || exit /b 1

REM Fit Slow/Normal/Fast from rights-cleared real transition durations in BEAT DOMAIN.
REM If supervision is still sparse this writes conservative defaults rather than inventing labels.
python training\fit_timing_calibration.py --index "%TR%" --out checkpoints\timing_calibration_v07.json --min-events 20 || exit /b 1

REM CC3 remains the user-facing vibrato depth axis. This expert learns depth/rate/onset/jitter separately.
python training\train_vibrato_expert.py --index "%TR%" --epochs 140 --batch 16 --out checkpoints\vibrato_expert_v07.pt
if errorlevel 3 (
  echo [INFO] Vibrato expert skipped: no rights-cleared vibrato_known frames in THIS training index.
) else if errorlevel 1 (
  exit /b 1
) else (
  set VIBARG=--vibrato-expert checkpoints\vibrato_expert_v07_best.pt
)

REM Independent physical experts use per-output masks. Timing supervision does NOT fabricate overlap/attack/softness targets.
python training\train_performance_experts.py --index "%TR%" --epochs 120 --batch 16 --out checkpoints\performance_experts_v07.pt
if errorlevel 3 (
  echo [INFO] Physical transition experts skipped: no rights-cleared aligned labels in THIS training index.
) else if errorlevel 1 (
  exit /b 1
) else (
  set PERFARG=--performance-experts checkpoints\performance_experts_v07_best.pt
)

REM HQ teacher embeds the exact supervised expert modules; valid expert checkpoints are warm-started/frozen for 12 epochs, then refined end-to-end.
python training\train_ballad_renderer.py --index "%TR%" --val-index "%VA%" --preset hq --epochs 240 --batch 2 --accum 2 %VIBARG% %PERFARG% --expert-freeze-epochs 12 --out checkpoints\hq_v07_last.pt --best-out checkpoints\hq_v07_best.pt || exit /b 1
python training\distill_renderer.py --index "%TR%" --teacher checkpoints\hq_v07_best.pt --epochs 110 --batch 2 --accum 2 --out checkpoints\compact_v07_distilled.pt || exit /b 1

echo.
echo [DONE] v0.7 beat-domain performance experts + HQ teacher + compact distillation finished.
endlocal
