@echo off
setlocal
cd /d "%~dp0.."
set E=release\evidence\v20
if not exist "%E%\acoustic_promotion.json" (echo [ERROR] acoustic_promotion.json missing. & exit /b 2)
for %%F in (sound_forge_report.json acoustic_segments_report.json codec_tournament_v20.json codec_abx_report.json generated_real_abx_report.json acoustic_promotion.json training_provenance.json release_metrics.json) do (
  if not exist "%E%\%%F" (echo [ERROR] Missing %E%\%%F & exit /b 2)
)
call scripts\SEAL_ACOUSTIC_PROMOTION_V20.bat "%E%\acoustic_promotion.json" checkpoints || exit /b 1
python training\scripts\build_release_model_manifest.py --model-dir checkpoints --provenance "%E%\training_provenance.json" --metrics "%E%\release_metrics.json" --approve --codec strings_vae64 --schema 7 --sound-forge-report "%E%\sound_forge_report.json" --codec-tournament "%E%\codec_tournament_v20.json" --codec-abx-report "%E%\codec_abx_report.json" --acoustic-segments "%E%\acoustic_segments_report.json" --generated-real-abx "%E%\generated_real_abx_report.json" --acoustic-promotion "%E%\acoustic_promotion.json" || exit /b 1
python training\scripts\commercial_release_gate.py --model-dir checkpoints || exit /b 1
python training\scripts\build_profile_model_packs.py --model-dir checkpoints --out-dir release\model_packs_v20 || exit /b 1
echo [PASS] v2.0 acoustic winner sealed and release packs created.
endlocal
