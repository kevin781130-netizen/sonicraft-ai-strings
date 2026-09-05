param([string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))))
$ErrorActionPreference='Continue';$root=(Resolve-Path $ProjectRoot).Path;$ev=Join-Path $root 'release\rc_evidence';New-Item -ItemType Directory -Force -Path $ev|Out-Null
$r=[ordered]@{schema=1;release='7.0.0-rc2';timestamp=(Get-Date).ToUniversalTime().ToString('o');checks=[ordered]@{}}
$r.checks.windows=($env:OS -eq 'Windows_NT')
$r.os=(Get-CimInstance Win32_OperatingSystem|Select-Object Caption,Version,BuildNumber)
$r.cpu=(Get-CimInstance Win32_Processor|Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors)
try{$gpu=& nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>$null;$r.gpu=$gpu;$r.checks.nvidia=[bool]$gpu}catch{$r.checks.nvidia=$false}
$r.checks.cmake=[bool](Get-Command cmake.exe -ErrorAction SilentlyContinue)
$r.checks.git=[bool](Get-Command git.exe -ErrorAction SilentlyContinue)
$r.checks.python=[bool](Get-Command python.exe -ErrorAction SilentlyContinue)
$r.checks.inno=[bool]((Test-Path "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe") -or (Test-Path "$env:ProgramFiles\Inno Setup 6\ISCC.exe"))
$r.checks.vst3_bundle=Test-Path (Join-Path $root 'release\SONICRAFT AI Strings Q4.vst3')
$cubase=Get-ChildItem 'C:\Program Files\Steinberg' -Recurse -File -Filter 'Cubase*.exe' -ErrorAction SilentlyContinue|Select-Object -First 1
$studio=Get-ChildItem 'C:\Program Files\PreSonus' -Recurse -File -Filter 'Studio One.exe' -ErrorAction SilentlyContinue|Select-Object -First 1
$r.cubase=if($cubase){[ordered]@{path=$cubase.FullName;version=$cubase.VersionInfo.ProductVersion}}else{$null}
$r.studio_one=if($studio){[ordered]@{path=$studio.FullName;version=$studio.VersionInfo.ProductVersion}}else{$null}
$r|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 (Join-Path $ev 'machine-preflight.json')
$r|ConvertTo-Json -Depth 8
