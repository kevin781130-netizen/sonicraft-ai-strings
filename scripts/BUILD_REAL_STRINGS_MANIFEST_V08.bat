@echo off
setlocal
cd /d "%~dp0\.."
if not exist datasets\manifests mkdir datasets\manifests
set OUT=datasets\manifests\real_strings_raw.jsonl
if exist "%OUT%" del "%OUT%"
set FOUND=0
if exist datasets\manifests\goodsounds_cora_2025.jsonl (
  type datasets\manifests\goodsounds_cora_2025.jsonl >> "%OUT%"
  set FOUND=1
)
REM Put any additional rights-cleared aligned recordings in this separate file so rebuilding does not overwrite them.
if exist datasets\manifests\real_strings_extra.jsonl (
  type datasets\manifests\real_strings_extra.jsonl >> "%OUT%"
  set FOUND=1
)
if "%FOUND%"=="0" (
  echo [INFO] No Expert-ready real source manifest found yet.
  echo Download Good-sounds CORA 2025 or create datasets\manifests\real_strings_extra.jsonl.
  exit /b 3
)
echo [DONE] Built %OUT%
endlocal
