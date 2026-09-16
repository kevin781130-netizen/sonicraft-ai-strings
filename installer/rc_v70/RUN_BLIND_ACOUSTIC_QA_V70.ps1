param(
  [string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))),
  [Parameter(Mandatory=$true)][string]$Protocol,
  [Parameter(Mandatory=$true)][string]$TrialPlan,
  [Parameter(Mandatory=$true)][string]$RawResults,
  [string]$PluginBinary='',
  [string]$ModelManifest='',
  [string]$Output=''
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path $ProjectRoot).Path
$tool=Join-Path $root 'training\blind_acoustic_release_v70.py'
if(-not(Test-Path $tool)){throw "Missing blind acoustic release tool: $tool"}

if(-not $ModelManifest){$ModelManifest=Join-Path $root 'release\prebuilt\Models\release_model_manifest.json'}
if(-not $Output){$Output=Join-Path $root 'release\rc_evidence\blind-acoustic-qa.json'}
if(-not $PluginBinary){
  $binDir=Join-Path $root 'release\SONICRAFT AI Strings Q4.vst3\Contents\x86_64-win'
  if(Test-Path $binDir){
    $candidate=Get-ChildItem $binDir -File -Filter '*.vst3'|Select-Object -First 1
    if($candidate){$PluginBinary=$candidate.FullName}
  }
}

foreach($pair in @(
  @('Protocol',$Protocol),
  @('TrialPlan',$TrialPlan),
  @('RawResults',$RawResults),
  @('PluginBinary',$PluginBinary),
  @('ModelManifest',$ModelManifest)
)){
  if(-not $pair[1] -or -not(Test-Path $pair[1])){throw "Missing $($pair[0]): $($pair[1])"}
}

$pythonExe=''
foreach($candidate in @(
  (Join-Path $root 'runtime\venv\Scripts\python.exe'),
  (Join-Path $root 'Runtime\venv\Scripts\python.exe')
)){
  if(Test-Path $candidate){$pythonExe=$candidate;break}
}
if(-not $pythonExe){
  $python=(Get-Command python.exe -ErrorAction SilentlyContinue)
  if(-not $python){$python=(Get-Command python -ErrorAction SilentlyContinue)}
  if($python){$pythonExe=$python.Source}
}
if(-not $pythonExe){throw 'Python is required to generate blind acoustic release evidence.'}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Output)|Out-Null
& $pythonExe $tool emit-evidence `
  --protocol $Protocol `
  --trial-plan $TrialPlan `
  --raw-results $RawResults `
  --plugin $PluginBinary `
  --model-manifest $ModelManifest `
  --out $Output
$ec=$LASTEXITCODE
if($ec -ne 0){
  Write-Host 'BLIND ACOUSTIC QA: BLOCKED. Evidence was not promoted.' -ForegroundColor Yellow
  exit $ec
}
Write-Host "BLIND ACOUSTIC QA: PASS -> $Output" -ForegroundColor Green
exit 0
