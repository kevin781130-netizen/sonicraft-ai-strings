param(
  [Parameter(Mandatory=$true)][string]$PythonHome,
  [Parameter(Mandatory=$true)][string]$ModelDir,
  [string]$OutDir = "$PSScriptRoot\..\release\NativeRuntime-v2.3",
  [double]$MaxMiB = 160.0
)
$ErrorActionPreference='Stop'
$Root=(Resolve-Path "$PSScriptRoot\..").Path
python "$Root\training\scripts\stage_embedded_ort_runtime_v23.py" --python-home $PythonHome --model-dir $ModelDir --out $OutDir --max-mib $MaxMiB
if($LASTEXITCODE -ne 0){ throw 'v2.3 embedded ORT staging failed' }
Write-Host "[PASS] v2.3 embedded ORT runtime staged at $OutDir"
