@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0.."
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 echo [INFO] No .venv activated; using current Python.

if not exist datasets\generated\cleanroom_bowed_v18\index.jsonl (
  echo [INFO] Generating independent physical-teacher lane...
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

if not exist datasets\forge\v20 mkdir datasets\forge\v20
if not exist release\evidence\v20 mkdir release\evidence\v20

 echo [1/9] Merge all commercial-audited acoustic material.
python training\scripts\merge_indexes.py !MERGEARGS! --out datasets\forge\v20\all_input.jsonl || exit /b 1

 echo [2/9] Sound Forge with v2.0 lane-locked curriculum.
python training\scripts\build_sound_forge_manifest.py --input datasets\forge\v20\all_input.jsonl --out datasets\forge\v20\eligible.jsonl --rejected datasets\forge\v20\rejected.jsonl --report release\evidence\v20\sound_forge_report.json --curriculum lane_locked_acoustic_promotion_v20 || exit /b 1

 echo [3/9] Phrase segmentation for codec learning/evaluation only; score-control timelines are NOT blindly cut.
python training\scripts\build_acoustic_segments.py --forge-manifest datasets\forge\v20\eligible.jsonl --out-dir datasets\forge\v20\segments_audio --out-manifest datasets\forge\v20\acoustic_segments.jsonl --report release\evidence\v20\acoustic_segments_report.json || exit /b 1

 echo [4/9] Train SONICRAFT VAE64 acoustic candidate. Candidate token selects v2.0 policy without pretending ABX already passed.
python training\train_codec.py --manifest datasets\forge\v20\acoustic_segments.jsonl --arch vae64 --width 24 --epochs 80 --batch 4 --real-ratio .80 --modeled-ratio .20 --modeled-recon-weight .20 --physics-weight .15 --physics-metric-weight .03 --require-modeled --acoustic-promotion CANDIDATE_V20 --out checkpoints\strings_vae64_v20.pt --decoder-out checkpoints\strings_vae64_decoder_v20.pt || exit /b 1

 echo [5/9] Forge renderer-control subset without destructive audio-only segmentation, then encode VAE64 latents.
python training\scripts\merge_indexes.py --index datasets\processed\ballad_isolated\index.jsonl --index datasets\generated\cleanroom_bowed_v18\index.jsonl --out datasets\forge\v20\renderer_input.jsonl || exit /b 1
python training\scripts\build_sound_forge_manifest.py --input datasets\forge\v20\renderer_input.jsonl --out datasets\forge\v20\renderer_eligible.jsonl --rejected datasets\forge\v20\renderer_rejected.jsonl --report datasets\forge\v20\renderer_report.json --curriculum lane_locked_acoustic_promotion_v20 || exit /b 1
python training\scripts\encode_vae64_latents.py --index datasets\forge\v20\renderer_eligible.jsonl --codec checkpoints\strings_vae64_v20.pt --out datasets\processed\ballad_vae64_v20 || exit /b 1
python training\scripts\check_release_sources.py --index datasets\processed\ballad_vae64_v20\index.jsonl --registry training\dataset_registry.json || exit /b 1
python training\scripts\split_by_group.py --index datasets\processed\ballad_vae64_v20\index.jsonl --train datasets\processed\ballad_vae64_v20\train.jsonl --val datasets\processed\ballad_vae64_v20\val.jsonl --val-percent 8 || exit /b 1

 echo [6/9] Train HQ acoustic candidate.
python training\train_ballad_renderer.py --index datasets\processed\ballad_vae64_v20\train.jsonl --val-index datasets\processed\ballad_vae64_v20\val.jsonl --preset hq_strings_v18 --epochs 240 --batch 2 --accum 2 --real-ratio .80 --modeled-ratio .20 --modeled-flow-weight .35 --acoustic-promotion CANDIDATE_V20 --out checkpoints\ballad_renderer_hq_v20_last.pt --best-out checkpoints\ballad_renderer_hq_v20_best.pt || exit /b 1

 echo [7/9] Distill to Frontier candidate.
python training\distill_renderer.py --index datasets\processed\ballad_vae64_v20\train.jsonl --teacher checkpoints\ballad_renderer_hq_v20_best.pt --student-preset frontier_core_dit --epochs 110 --batch 2 --accum 2 --real-ratio .80 --modeled-ratio .20 --modeled-flow-weight .35 --acoustic-promotion CANDIDATE_V20 --out checkpoints\ballad_renderer_frontier_v20_distilled.pt || exit /b 1

 echo [8/9] Shortcut 1/2/4/8-step candidate.
python training\shortcut_distill_renderer.py --index datasets\processed\ballad_vae64_v20\train.jsonl --init checkpoints\ballad_renderer_frontier_v20_distilled.pt --preset frontier_core_dit --max-steps 8 --recommend-steps 2 --epochs 45 --batch 1 --real-ratio .80 --modeled-ratio .20 --modeled-flow-weight .35 --acoustic-promotion CANDIDATE_V20 --out checkpoints\ballad_renderer_frontier_v20_shortcut.pt || exit /b 1

 echo [9/9] Engineering regression. No model is promoted by this step.
python training\smoke_v20.py || exit /b 1

echo.
echo [CANDIDATES READY]
echo Next: reconstruct the SAME real held-out references through VAE64 / ACE 25Hz / APCodec challengers.
echo Then run v2.0 codec tournament + codec ABX + generated-vs-real ABX.
echo Only after both listening gates pass: RUN_ACOUSTIC_PROMOTION_V20.bat then SEAL_ACOUSTIC_PROMOTION_V20.bat.
endlocal
