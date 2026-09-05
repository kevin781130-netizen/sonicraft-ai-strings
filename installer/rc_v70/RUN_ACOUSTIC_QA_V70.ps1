param(
  [string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))),
  [string]$ModelDir='',
  [string]$Checkpoint='',
  [string]$Score='',
  [string]$Store=''
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path $ProjectRoot).Path
$ev=Join-Path $root 'release\rc_evidence';New-Item -ItemType Directory -Force -Path $ev|Out-Null
if(-not $ModelDir){$ModelDir=Join-Path $root 'release\prebuilt\Models'}
$manifest=Join-Path $ModelDir 'release_model_manifest.json'
$report=[ordered]@{schema=1;product='SONICRAFT AI Strings Q4';release='7.0.0-rc2';tested_at=(Get-Date).ToUniversalTime().ToString('o');overall='BLOCKED';checks=[ordered]@{}}
$bundle=Join-Path $root 'release\SONICRAFT AI Strings Q4.vst3'
if(Test-Path $bundle){$bin=Get-ChildItem (Join-Path $bundle 'Contents\x86_64-win') -File -Filter '*.vst3'|Select-Object -First 1;if($bin){$report.plugin_sha256=(Get-FileHash $bin.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}}
$report.checks.windows=($env:OS -eq 'Windows_NT')
try{
  $gpu=& nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>$null
  $report.checks.nvidia_gpu=[bool]$gpu;$report.gpu=$gpu
  $report.checks.rtx5090=([string]$gpu -match '5090')
}catch{$report.checks.nvidia_gpu=$false;$report.checks.rtx5090=$false}
$report.checks.model_manifest=Test-Path $manifest
if(Test-Path $manifest){
  try{
    $report.model_manifest_sha256=(Get-FileHash $manifest -Algorithm SHA256).Hash.ToLowerInvariant()
    $m=Get-Content $manifest -Raw|ConvertFrom-Json
    $report.model_manifest=[ordered]@{commercial_safe=[bool]$m.commercial_safe;release_approved=[bool]$m.release_approved;path=$manifest}
    $report.checks.model_approved=([bool]$m.commercial_safe -and [bool]$m.release_approved)
    $hashOk=$true
    foreach($f in $m.files){
      $p=Join-Path $ModelDir $f.name
      if(-not(Test-Path $p)){$hashOk=$false;break}
      $h=(Get-FileHash $p -Algorithm SHA256).Hash.ToLowerInvariant()
      if($h -ne ([string]$f.sha256).ToLowerInvariant()){$hashOk=$false;break}
    }
    $report.checks.model_hashes=$hashOk
  }catch{$report.checks.model_approved=$false;$report.checks.model_hashes=$false;$report.model_error=$_.Exception.Message}
}else{$report.checks.model_approved=$false;$report.checks.model_hashes=$false}

$py=(Get-Command python.exe -ErrorAction SilentlyContinue)
$report.checks.python=[bool]$py
if($Checkpoint -and $Score -and $Store -and $py){
  $cpTool=Join-Path $root 'runtime\performance_checkpoint_v62.py'
  if((Test-Path $cpTool) -and (Test-Path $Checkpoint) -and (Test-Path $Score) -and (Test-Path $Store)){
    $log=Join-Path $ev 'acoustic-checkpoint-verify.log'
    & $py.Source $cpTool verify $Checkpoint --score $Score --store $Store --backend auto --model-dir $ModelDir 2>&1|Tee-Object -FilePath $log|Out-Host
    $report.checks.checkpoint_verify=($LASTEXITCODE -eq 0)
  }else{$report.checks.checkpoint_verify=$false}
}else{
  $report.checks.checkpoint_verify=$false
  $report.checkpoint_note='Provide -Checkpoint, -Score and -Store after a real model render to close this gate.'
}

$required=@('windows','nvidia_gpu','rtx5090','model_manifest','model_approved','model_hashes','python','checkpoint_verify')
$pass=$true;foreach($k in $required){if(-not [bool]$report.checks[$k]){$pass=$false}}
if($pass){$report.overall='PASS'}
$path=Join-Path $ev 'acoustic-qa.json';$report|ConvertTo-Json -Depth 10|Set-Content -Encoding UTF8 $path
$report|ConvertTo-Json -Depth 10|Out-Host
if(-not$pass){Write-Host 'ACOUSTIC QA BLOCKED. This is expected until the final approved model + RTX 5090 real render evidence exist.' -ForegroundColor Yellow;exit 2}
Write-Host 'ACOUSTIC QA PASS.' -ForegroundColor Green
