@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0.."
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 echo [INFO] No .venv activated; using current Python.

if not exist datasets\generated\cleanroom_bowed_v18\index.jsonl (
  echo [INFO] Generating independent physical teacher lane...
  call scripts\GENERATE_CLEANROOM_STRINGS_V18.bat || exit /b 1
)
if not exist datasets\processed\ballad_isolated\index.jsonl (
  echo [ERROR] Missing rights-cleared performance/control index: datasets\processed\ballad_isolated\index.jsonl
  exit /b 2
)

set MERGEARGS=--index datasets\processed\ballad_isolated\index.jsonl --index datasets\generated\cleanroom_bowed_v18\index.jsonl
for %%F in (datasets\manifests\iowa_strings.jsonl datasets\manifests\tinysol_strings.jsonl datasets\manifests\goodsounds_cora_2025.jsonl datasets\manifests\ghent_ar_violin_2023.jsonl datasets\raw\ghent_ar_violin_2023\manifest.jsonl datasets\manifests\sanidha_violin.jsonl datasets\manifests\musicnet_strings_safe.jsonl datasets\manifests\vsco2_ce_strings.jsonl) do (
  if exist %%F set MERGEARGS=!MERGEARGS! --index %%F
)

if not exist datasets\forge\v19 mkdir datasets\forge\v19
if not exist release\evidence mkdir release\evidence

echo [1/8] Merge all audio ever allowed to influence v1.9 acoustic weights.
python training\scripts\merge_indexes.py !MERGEARGS! --out datasets\forge\v19\all_input.jsonl || exit /b 1

echo [2/8] Sound Forge: registry rights + hashes + duplicate removal + recording-quality grading.
python training\scripts\build_sound_forge_manifest.py --input datasets\forge\v19\all_input.jsonl --out datasets\forge\v19\eligible.jsonl --rejected datasets\forge\v19\rejected.jsonl --report release\evidence\sound_forge_report.json || exit /b 1

echo [3/8] Train VAE64. Sampling stays exactly 80%% REAL / 20%% MODELED; adversarial real target remains REAL-only.
python training\train_codec.py --manifest datasets\forge\v19\eligible.jsonl --arch vae64 --width 24 --epochs 80 --batch 4 --real-ratio .80 --modeled-ratio .20 --modeled-recon-weight .20 --physics-weight .15 --physics-metric-weight .03 --require-modeled --out checkpoints\strings_vae64_v19.pt --decoder-out checkpoints\strings_vae64_decoder_v19.pt || exit /b 1

echo [4/8] Forge the renderer-control subset and encode VAE64 latents with Forge quality metadata preserved.
python training\scripts\merge_indexes.py --index datasets\processed\ballad_isolated\index.jsonl --index datasets\generated\cleanroom_bowed_v18\index.jsonl --out datasets\forge\v19\renderer_input.jsonl || exit /b 1
python training\scripts\build_sound_forge_manifest.py --input datasets\forge\v19\renderer_input.jsonl --out datasets\forge\v19\renderer_eligible.jsonl --rejected datasets\forge\v19\renderer_rejected.jsonl --report datasets\forge\v19\renderer_report.json || exit /b 1
python training\scripts\encode_vae64_latents.py --index datasets\forge\v19\renderer_eligible.jsonl --codec checkpoints\strings_vae64_v19.pt --out datasets\processed\ballad_vae64_v19 || exit /b 1
python training\scripts\check_release_sources.py --index datasets\processed\ballad_vae64_v19\index.jsonl --registry training\dataset_registry.json || exit /b 1
python training\scripts\split_by_group.py --index datasets\processed\ballad_vae64_v19\index.jsonl --train datasets\processed\ballad_vae64_v19\train.jsonl --val datasets\processed\ballad_vae64_v19\val.jsonl --val-percent 8 || exit /b 1

echo [5/8] Train the high-capacity rights-cleared teacher.
python training\train_ballad_renderer.py --index datasets\processed\ballad_vae64_v19\train.jsonl --val-index datasets\processed\ballad_vae64_v19\val.jsonl --preset hq_strings_v18 --epochs 240 --batch 2 --accum 2 --real-ratio .80 --modeled-ratio .20 --modeled-flow-weight .35 --out checkpoints\ballad_renderer_hq_v19_last.pt --best-out checkpoints\ballad_renderer_hq_v19_best.pt || exit /b 1

echo [6/8] Distill to one tiny Frontier renderer.
python training\distill_renderer.py --index datasets\processed\ballad_vae64_v19\train.jsonl --teacher checkpoints\ballad_renderer_hq_v19_best.pt --student-preset frontier_core_dit --epochs 110 --batch 2 --accum 2 --real-ratio .80 --modeled-ratio .20 --modeled-flow-weight .35 --out checkpoints\ballad_renderer_frontier_v19_distilled.pt || exit /b 1

echo [7/8] Shortcut one/few-step specialization; still one shipping network.
python training\shortcut_distill_renderer.py --index datasets\processed\ballad_vae64_v19\train.jsonl --init checkpoints\ballad_renderer_frontier_v19_distilled.pt --preset frontier_core_dit --max-steps 8 --recommend-steps 2 --epochs 45 --batch 1 --real-ratio .80 --modeled-ratio .20 --modeled-flow-weight .35 --out checkpoints\ballad_renderer_frontier_v19_shortcut.pt || exit /b 1

echo [8/8] Engineering regression. Acoustic promotion remains blocked until codec tournament + two blind listening gates pass.
python training\smoke_v19.py || exit /b 1

echo.
echo [DONE] v1.9 Sound Forge training chain complete.
echo Next: scripts\PREP_CODEC_TOURNAMENT_V19.bat, reconstruct each challenger, then RUN_CODEC_TOURNAMENT_V19.bat and BUILD_CODEC_ABX_V19.bat.
endlocal
