param([string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),[string]$Out='')
$ErrorActionPreference='Continue'; $root=(Resolve-Path $ProjectRoot).Path
if(-not $Out){$Out=Join-Path $root 'release\machine_qa_report.json'}
$AppDir=Join-Path $env:LOCALAPPDATA 'SONICRAFT\AI Strings Q4'; $Vst=Join-Path $env:LOCALAPPDATA 'Programs\Common\VST3\SONICRAFT AI Strings Q4.vst3'
$checks=[ordered]@{}
$checks.windows=($env:OS -eq 'Windows_NT')
$checks.vst3_installed=Test-Path $Vst
$checks.runtime_python=Test-Path (Join-Path $AppDir 'Runtime\venv\Scripts\python.exe')
$checks.model_manifest=Test-Path (Join-Path $AppDir 'Models\release_model_manifest.json')
try{$gpu=& nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>$null; $checks.nvidia_gpu=([bool]$gpu); $checks.gpu=$gpu}catch{$checks.nvidia_gpu=$false}
$validator=Get-ChildItem $root -Recurse -Filter validator.exe -ErrorAction SilentlyContinue|Select-Object -First 1
$checks.validator_found=[bool]$validator
if($validator -and (Test-Path $Vst)){try{& $validator.FullName $Vst | Out-Null; $checks.validator_pass=($LASTEXITCODE -eq 0)}catch{$checks.validator_pass=$false}}else{$checks.validator_pass=$false}
$checks.cubase_manual_required=$true
$checks.cubase_manual_items=@('Load VST3','Save/reopen project','CC1/CC3/CC11 sample-accurate automation','12 articulations / Expression Map','Tempo ramp transition timing','AUTO fallback when renderer stopped','Offline export HQ','Multiple instances shared renderer')
$checks.timestamp=(Get-Date).ToString('o')
New-Item -ItemType Directory -Force -Path (Split-Path $Out -Parent)|Out-Null; $checks|ConvertTo-Json -Depth 5|Set-Content -Encoding UTF8 $Out
$checks|ConvertTo-Json -Depth 5
