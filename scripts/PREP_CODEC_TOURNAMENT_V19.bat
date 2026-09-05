@echo off
setlocal
cd /d "%~dp0.."
if not exist datasets\forge\v19\eligible.jsonl (echo [ERROR] Run TRAIN_STRINGS_SOUND_FORGE_V19.bat first.& exit /b 2)
python training\scripts\prepare_codec_eval.py --forge-manifest datasets\forge\v19\eligible.jsonl --out-dir datasets\eval\codec_v19 --max-clips 64 || exit /b 1
if exist checkpoints\strings_vae64_v19.pt (
  python training\scripts\reconstruct_vae64_eval.py --refs datasets\eval\codec_v19\codec_eval_refs.jsonl --checkpoint checkpoints\strings_vae64_v19.pt --out-dir datasets\eval\codec_v19\recon_sonicraft_vae64 || exit /b 1
  python training\scripts\build_codec_pairs_from_dir.py --refs datasets\eval\codec_v19\codec_eval_refs.jsonl --recon-dir datasets\eval\codec_v19\recon_sonicraft_vae64 --candidate-id sonicraft_vae64 --kind strings_vae64 --latent-ch 64 --latent-hz 30 --out datasets\eval\codec_v19\pairs.jsonl || exit /b 1
)
echo [NEXT] Round-trip the same numbered reference files through ACE-Step/Oobleck or other legal challengers.
echo Then append them with training\scripts\build_codec_pairs_from_dir.py and run scripts\RUN_CODEC_TOURNAMENT_V19.bat.
endlocal
