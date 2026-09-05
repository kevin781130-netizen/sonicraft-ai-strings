@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0.."

if not exist .venv\Scripts\python.exe (
  echo [ERROR] Run scripts\SETUP_TRAINING.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
if not exist checkpoints mkdir checkpoints
if not exist datasets\processed mkdir datasets\processed

set IOWA=datasets\manifests\iowa_strings.jsonl
set TINY=datasets\manifests\tinysol_strings.jsonl
set GOOD=datasets\manifests\good_sounds_cora_2025.jsonl
set GHENT=datasets\raw\ghent_ar_violin_2023\manifest.jsonl
set SANIDHA=datasets\manifests\sanidha_violin.jsonl

if not exist "%IOWA%" (
  echo [ERROR] Iowa is the required HQ timbre anchor.
  echo Run scripts\DOWNLOAD_IOWA_STRINGS.bat first.
  goto :fail
)

rem Acoustic codec can use any rights-cleared real-string audio, even without MIDI alignment.
set CODEC_ARGS=--manifest "%IOWA%"
if exist "%GOOD%" set CODEC_ARGS=!CODEC_ARGS! --manifest "%GOOD%"
if exist "%GHENT%" set CODEC_ARGS=!CODEC_ARGS! --manifest "%GHENT%"
if exist "%SANIDHA%" set CODEC_ARGS=!CODEC_ARGS! --manifest "%SANIDHA%"
if exist "%TINY%" set CODEC_ARGS=!CODEC_ARGS! --manifest "%TINY%"

rem MIDI-conditioned bootstrap only accepts material with defensible note labels.
set RENDER_ARGS=--manifest "%IOWA%"
if exist "%GOOD%" set RENDER_ARGS=!RENDER_ARGS! --manifest "%GOOD%"
if exist "%TINY%" set RENDER_ARGS=!RENDER_ARGS! --manifest "%TINY%"

python training\scripts\check_release_sources.py !CODEC_ARGS! --dataset descript_dac --out checkpoints\v04_codec_provenance.json
if errorlevel 1 goto :fail
python training\scripts\check_release_sources.py !RENDER_ARGS! --dataset descript_dac --out checkpoints\v04_renderer_provenance.json
if errorlevel 1 goto :fail

echo.
echo [1/5] Fine-tune Strings DAC decoder with available commercial-safe acoustic sources.
python training\train_dac_decoder.py !CODEC_ARGS! --out checkpoints\dac_strings_decoder_v04.pt --epochs 40 --batch 3 --seconds 2.0 --bitrate 16kbps
if errorlevel 1 goto :fail

echo.
echo [2/5] Build only defensibly labeled MIDI controls.
echo       Scale recordings remain acoustic data; they are NOT mislabeled as one MIDI note.
python training\scripts\prepare_isolated_controls.py !RENDER_ARGS! --out datasets\processed\ballad_isolated_v04\index.jsonl
if errorlevel 1 goto :fail

echo.
echo [3/5] Encode to continuous DAC latents. Unknown CC3/CC11/pitch-bend labels stay masked.
python training\scripts\encode_dac_latents.py --index datasets\processed\ballad_isolated_v04\index.jsonl --out datasets\processed\ballad_dac_v04 --seconds 2.0 --bitrate 16kbps
if errorlevel 1 goto :fail

echo.
echo [4/5] Train compact commercial bootstrap renderer.
python training\train_ballad_renderer.py --index datasets\processed\ballad_dac_v04\index.jsonl --out checkpoints\mandarin_ballad_q4_v04_compact.pt --preset compact --epochs 120 --batch 2
if errorlevel 1 goto :fail

echo.
echo [5/5] Train HQ renderer separately; on RTX-class 24GB+ cards this is the preferred release candidate branch.
python training\train_ballad_renderer.py --index datasets\processed\ballad_dac_v04\index.jsonl --out checkpoints\mandarin_ballad_q4_v04_hq.pt --preset hq --epochs 160 --batch 1
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo V0.4 PUBLIC-DATA BOOTSTRAP COMPLETE.
echo The checkpoint is still NOT allowed to be called recording-indistinguishable.
echo CC3/vibrato and lyrical legato quality remain gated by truly labeled real-performance data.
echo Final stage: rights-cleared owned Q4 transition session + ABX.
echo ============================================================
pause
exit /b 0

:fail
echo.
echo [ERROR] Training stopped. No source-policy bypass is permitted.
pause
exit /b 1
