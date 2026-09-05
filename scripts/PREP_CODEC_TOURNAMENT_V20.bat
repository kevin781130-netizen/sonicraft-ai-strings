@echo off
setlocal
cd /d "%~dp0.."
if not exist datasets\forge\v20\eligible.jsonl (echo [ERROR] Run TRAIN_STRINGS_ACOUSTIC_CANDIDATES_V20.bat first. & exit /b 2)
if not exist datasets\eval\codec_v20 mkdir datasets\eval\codec_v20
python training\scripts\prepare_codec_eval.py --forge-manifest datasets\forge\v20\eligible.jsonl --out-dir datasets\eval\codec_v20 --max-clips 96 || exit /b 1
if exist checkpoints\strings_vae64_v20.pt (
  python training\scripts\reconstruct_vae64_eval.py --refs datasets\eval\codec_v20\codec_eval_refs.jsonl --checkpoint checkpoints\strings_vae64_v20.pt --out-dir datasets\eval\codec_v20\recon_sonicraft_vae64 || exit /b 1
  python training\scripts\build_codec_pairs_from_dir.py --refs datasets\eval\codec_v20\codec_eval_refs.jsonl --recon-dir datasets\eval\codec_v20\recon_sonicraft_vae64 --candidate-id sonicraft_vae64 --kind strings_vae64 --latent-ch 64 --latent-hz 30 --out datasets\eval\codec_v20\pairs.jsonl || exit /b 1
)
echo.
echo [NEXT] Round-trip these exact numbered references through:
echo   1. ACE-Step/Oobleck 64-d 25Hz challenger
 echo  2. APCodec 48k challenger
 echo Append each reconstruction set with build_codec_pairs_from_dir.py.
echo Do NOT use upstream generic weights for final promotion; use weights retrained/fine-tuned on audited SONICRAFT data where license permits.
endlocal
