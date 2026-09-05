@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0.."
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 echo [INFO] No .venv activated; using current Python.

set REALARGS=
if exist datasets\manifests\iowa_strings.jsonl set REALARGS=!REALARGS! --manifest datasets\manifests\iowa_strings.jsonl
if exist datasets\manifests\tinysol_strings.jsonl set REALARGS=!REALARGS! --manifest datasets\manifests\tinysol_strings.jsonl
if exist datasets\manifests\goodsounds_cora_2025.jsonl set REALARGS=!REALARGS! --manifest datasets\manifests\goodsounds_cora_2025.jsonl
if exist datasets\manifests\ghent_ar_violin_2023.jsonl set REALARGS=!REALARGS! --manifest datasets\manifests\ghent_ar_violin_2023.jsonl
if exist datasets\raw\ghent_ar_violin_2023\manifest.jsonl set REALARGS=!REALARGS! --manifest datasets\raw\ghent_ar_violin_2023\manifest.jsonl
if exist datasets\manifests\sanidha_violin.jsonl set REALARGS=!REALARGS! --manifest datasets\manifests\sanidha_violin.jsonl
if exist datasets\manifests\musicnet_strings_safe.jsonl set REALARGS=!REALARGS! --manifest datasets\manifests\musicnet_strings_safe.jsonl
if exist datasets\manifests\vsco2_ce_strings.jsonl set REALARGS=!REALARGS! --manifest datasets\manifests\vsco2_ce_strings.jsonl
if "!REALARGS!"=="" (
  echo [ERROR] No commercial-safe REAL string manifests found.
  echo Download/prepare at least Iowa, TinySOL, GoodSounds CORA, audited Ghent/Sanidha/MusicNet, or another registry-approved real source first.
  exit /b 2
)
if not exist datasets\generated\cleanroom_bowed_v18\index.jsonl (
  echo [INFO] Generating independent physical teacher lane...
  call scripts\GENERATE_CLEANROOM_STRINGS_V18.bat || exit /b 1
)
if not exist datasets\processed\ballad_isolated\index.jsonl (
  echo [ERROR] Missing rights-cleared REAL performance/control index: datasets\processed\ballad_isolated\index.jsonl
  exit /b 2
)

echo [1/8] Train VAE64 with fixed 80%% REAL / 20%% MODELED sampling. Discriminator sees REAL only.
python training\train_codec.py !REALARGS! --manifest datasets\generated\cleanroom_bowed_v18\index.jsonl --arch vae64 --width 24 --epochs 80 --batch 4 --real-ratio .80 --modeled-ratio .20 --modeled-recon-weight .20 --physics-weight .15 --require-modeled --out checkpoints\strings_vae64_v18.pt --decoder-out checkpoints\strings_vae64_decoder_v18.pt || exit /b 1

echo [2/8] Encode real string performance latents.
python training\scripts\encode_vae64_latents.py --index datasets\processed\ballad_isolated\index.jsonl --codec checkpoints\strings_vae64_v18.pt --out datasets\processed\ballad_vae64_v18_real || exit /b 1

echo [3/8] Encode modeled physical-teacher latents with exact control labels.
python training\scripts\encode_vae64_latents.py --index datasets\generated\cleanroom_bowed_v18\index.jsonl --codec checkpoints\strings_vae64_v18.pt --out datasets\processed\ballad_vae64_v18_modeled || exit /b 1

echo [4/8] Merge + commercial-source gate.
python training\scripts\merge_indexes.py --index datasets\processed\ballad_vae64_v18_real\index.jsonl --index datasets\processed\ballad_vae64_v18_modeled\index.jsonl --out datasets\processed\ballad_vae64_v18\index.jsonl || exit /b 1
python training\scripts\check_release_sources.py --index datasets\processed\ballad_vae64_v18\index.jsonl --registry training\dataset_registry.json || exit /b 1
python training\scripts\split_by_group.py --index datasets\processed\ballad_vae64_v18\index.jsonl --train datasets\processed\ballad_vae64_v18\train.jsonl --val datasets\processed\ballad_vae64_v18\val.jsonl --val-percent 8 || exit /b 1

echo [5/8] Train high-capacity real-dominant string teacher.
python training\train_ballad_renderer.py --index datasets\processed\ballad_vae64_v18\train.jsonl --val-index datasets\processed\ballad_vae64_v18\val.jsonl --preset hq_strings_v18 --epochs 240 --batch 2 --accum 2 --real-ratio .80 --modeled-ratio .20 --modeled-flow-weight .35 --out checkpoints\ballad_renderer_hq_v18_last.pt --best-out checkpoints\ballad_renderer_hq_v18_best.pt || exit /b 1

echo [6/8] Distill to the compact v1.8 Frontier Core.
python training\distill_renderer.py --index datasets\processed\ballad_vae64_v18\train.jsonl --teacher checkpoints\ballad_renderer_hq_v18_best.pt --student-preset frontier_core_dit --epochs 110 --batch 2 --accum 2 --real-ratio .80 --modeled-ratio .20 --modeled-flow-weight .35 --out checkpoints\ballad_renderer_frontier_v18_distilled.pt || exit /b 1

echo [7/8] Shortcut one/few-step specialization; one network still ships.
python training\shortcut_distill_renderer.py --index datasets\processed\ballad_vae64_v18\train.jsonl --init checkpoints\ballad_renderer_frontier_v18_distilled.pt --preset frontier_core_dit --max-steps 8 --recommend-steps 2 --epochs 45 --batch 1 --real-ratio .80 --modeled-ratio .20 --modeled-flow-weight .35 --out checkpoints\ballad_renderer_frontier_v18_shortcut.pt || exit /b 1

echo [8/8] Regression / origin mix / clean-room policy tests.
python training\smoke_v18.py || exit /b 1
python training\smoke_string_mix_v18.py || exit /b 1
python training\smoke_release_policy_v18.py || exit /b 1

echo.
echo [DONE] v1.8 REAL80 / MODEL20 string-sound training chain completed.
echo Acoustic promotion still requires held-out real-string ABX; modeled data is never the final timbre anchor.
endlocal
