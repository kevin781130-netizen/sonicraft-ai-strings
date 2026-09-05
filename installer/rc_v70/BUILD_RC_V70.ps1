param(
  [string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))),
  [string]$ApprovedModelDir='',
  [string]$OrtSdkRoot='',
  [switch]$BuildInstaller
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path $ProjectRoot).Path
$ev=Join-Path $root 'release\rc_evidence'
New-Item -ItemType Directory -Force -Path $ev|Out-Null
Write-Host 'SONICRAFT AI Strings Q4 v7.0 RC2 BUILD PIPELINE' -ForegroundColor Cyan
Write-Host 'Core v6.2 + Frontend v6.4 are frozen. This pipeline only builds/packages/validates the RC.' -ForegroundColor DarkGray

Write-Host '[1/6] Pinned VST3 build + official Steinberg Validator' -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\build_release_windows.ps1') -ProjectRoot $root
if($LASTEXITCODE -ne 0){throw 'VST3 build/validator gate failed'}

Write-Host '[2/6] Native Windows Product Shell' -ForegroundColor Cyan
$shellArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $root 'installer\BUILD_PRODUCT_SHELL_V26.ps1'),'-ProjectRoot',$root)
if($OrtSdkRoot){$shellArgs+=@('-OrtSdkRoot',$OrtSdkRoot)}
& powershell.exe @shellArgs
if($LASTEXITCODE -ne 0){throw 'Product Shell build failed'}

Write-Host '[3/6] Stage the EXACT already-validated VST3 + consumer app' -ForegroundColor Cyan
$stage=Join-Path $root 'release\prebuilt'
$srcVst=Join-Path $root 'release\SONICRAFT AI Strings Q4.vst3'
$dstVst=Join-Path $stage 'VST3\SONICRAFT AI Strings Q4.vst3'
New-Item -ItemType Directory -Force -Path (Split-Path $dstVst -Parent)|Out-Null
if(Test-Path $dstVst){Remove-Item -Recurse -Force $dstVst}
Copy-Item -Recurse -Force $srcVst $dstVst
$validatorEvidence=Join-Path $root 'release\rc_evidence\validator-pass.json'
if(-not(Test-Path $validatorEvidence)){throw 'Validator evidence missing after build'}
Copy-Item -Force $validatorEvidence (Join-Path $stage 'validator-pass.json')
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\COLLECT_PREBUILT_APP.ps1') -ProjectRoot $root
if($LASTEXITCODE -ne 0){throw 'Consumer app staging failed'}

if($ApprovedModelDir){
  Write-Host '[4/6] Stage approved model pack' -ForegroundColor Cyan
  $manifest=Join-Path $ApprovedModelDir 'release_model_manifest.json'
  if(-not(Test-Path $manifest)){throw 'ApprovedModelDir has no release_model_manifest.json'}
  $m=Get-Content $manifest -Raw|ConvertFrom-Json
  if(-not($m.commercial_safe -and $m.release_approved)){throw 'Model manifest is not commercial_safe + release_approved'}
  $dest=Join-Path $stage 'Models'
  if(Test-Path $dest){Remove-Item -Recurse -Force $dest}
  New-Item -ItemType Directory -Force -Path $dest|Out-Null
  Copy-Item -Recurse -Force (Join-Path $ApprovedModelDir '*') $dest
}else{
  Write-Host '[4/6] Model pack intentionally absent: RC remains acoustic-gate BLOCKED.' -ForegroundColor Yellow
}

Write-Host '[5/6] Immutable payload manifest + fail-closed layout verification' -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\GENERATE_PREBUILT_MANIFEST.ps1') -ProjectRoot $root
if($LASTEXITCODE -ne 0){throw 'Prebuilt manifest generation failed'}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\VERIFY_PREBUILT_RELEASE.ps1') -ProjectRoot $root -RequireModels:([bool]$ApprovedModelDir)
if($LASTEXITCODE -ne 0){throw 'Prebuilt payload verification failed'}

if($BuildInstaller){
  Write-Host '[6/6] Build Inno Setup installer' -ForegroundColor Cyan
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\BUILD_FINAL_INNO_INSTALLER.ps1') -ProjectRoot $root -Version '7.0.0-rc2' -RequireModels:([bool]$ApprovedModelDir)
  if($LASTEXITCODE -ne 0){throw 'Installer build failed'}
}else{
  Write-Host '[6/6] Installer not requested. Re-run with -BuildInstaller when desired.' -ForegroundColor DarkGray
}

$summary=[ordered]@{
 schema=1; product='SONICRAFT AI Strings Q4'; release='7.0.0-rc2'; status='BUILD_STAGE_PASS';
 completed_at=(Get-Date).ToUniversalTime().ToString('o'); models_staged=[bool]$ApprovedModelDir;
 validator='PASS'; product_shell='PASS'; payload_layout='PASS'; installer_built=[bool]$BuildInstaller;
 remaining_required_gates=@('Cubase real-host QA','Studio One real-host QA','RTX 5090 acoustic QA','final trained/approved model pack')
}
$summary|ConvertTo-Json -Depth 6|Set-Content -Encoding UTF8 (Join-Path $ev 'rc-build-stage.json')
Write-Host 'v7.0 RC BUILD STAGE PASS. Host/acoustic gates are still separate and fail-closed.' -ForegroundColor Green
