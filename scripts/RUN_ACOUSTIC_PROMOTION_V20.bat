@echo off
setlocal
cd /d "%~dp0.."

if "%~1"=="" (
  echo Usage: scripts\RUN_ACOUSTIC_PROMOTION_V20.bat ^<workspace^>
  echo Workspace must contain forge_manifest.jsonl, sound_forge_report.json, codec_pairs.jsonl,
  echo codec_abx_report.json and generated_real_abx_report.json after listening tests.
  exit /b 2
)
set W=%~1
if not exist "%W%" mkdir "%W%"

if not exist "%W%\forge_manifest.jsonl" (
  echo [ERROR] Missing %W%\forge_manifest.jsonl
  exit /b 2
)

python training\scripts\build_acoustic_segments.py --forge-manifest "%W%\forge_manifest.jsonl" --out-dir "%W%\segments" --out-manifest "%W%\acoustic_segments.jsonl" --report "%W%\acoustic_segments_report.json"
if errorlevel 1 exit /b %errorlevel%

if exist "%W%\codec_pairs.jsonl" (
  python training\scripts\run_codec_tournament_v20.py --pairs "%W%\codec_pairs.jsonl" --out "%W%\codec_tournament_v20.json"
  if errorlevel 1 exit /b %errorlevel%
) else (
  echo [NEXT] Produce reconstructions for VAE64 / ACE 25Hz / APCodec challengers and write %W%\codec_pairs.jsonl
  exit /b 3
)

if not exist "%W%\codec_abx_report.json" (
  echo [NEXT] Run blind codec ABX and create %W%\codec_abx_report.json
  exit /b 3
)
if not exist "%W%\generated_real_abx_report.json" (
  echo [NEXT] Run generated-vs-real blind ABX and create %W%\generated_real_abx_report.json
  exit /b 3
)

for /f "usebackq delims=" %%C in (`python -c "import json;print(json.load(open(r'%W%\\codec_tournament_v20.json'))['winner_kind'])"`) do set CODEC=%%C
python training\scripts\build_acoustic_promotion.py --sound-forge "%W%\sound_forge_report.json" --segments "%W%\acoustic_segments_report.json" --codec-tournament "%W%\codec_tournament_v20.json" --codec-abx "%W%\codec_abx_report.json" --generated-real-abx "%W%\generated_real_abx_report.json" --shipping-codec "%CODEC%" --out "%W%\acoustic_promotion.json"
if errorlevel 1 (
  echo [BLOCKED] Tournament winner is not yet an audited SONICRAFT runtime codec or evidence failed.
  exit /b %errorlevel%
)

echo.
echo ACOUSTIC PROMOTION PASS
for /f "usebackq delims=" %%P in (`python -c "import json;print(json.load(open(r'%W%\\acoustic_promotion.json'))['promotion_id'])"`) do echo Promotion ID: %%P
endlocal
