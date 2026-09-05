$ErrorActionPreference='SilentlyContinue'
Write-Host 'SONICRAFT AI Strings Q4 v7.0 RC2 - Windows Build Environment Check' -ForegroundColor Cyan
$ok=$true
foreach($c in @('cmake','git','powershell.exe')) {
  $x=Get-Command $c -ErrorAction SilentlyContinue
  if($x){ Write-Host "[OK] $c -> $($x.Source)" -ForegroundColor Green }
  else { Write-Host "[MISSING] $c" -ForegroundColor Yellow; $ok=$false }
}
$vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if(Test-Path $vswhere){
  $vs=& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
  if($vs){ Write-Host "[OK] MSVC x64 -> $vs" -ForegroundColor Green }
  else { Write-Host '[MISSING] Visual Studio 2022 Build Tools - Desktop development with C++' -ForegroundColor Yellow; $ok=$false }
} else { Write-Host '[MISSING] Visual Studio Installer / vswhere' -ForegroundColor Yellow; $ok=$false }
$cuda=& nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null
if($LASTEXITCODE -eq 0 -and $cuda){ Write-Host "[GPU] $cuda" -ForegroundColor Green } else { Write-Host '[GPU] NVIDIA CUDA GPU not detected (LIVE preview can still run; HQ training/render needs CUDA).' -ForegroundColor DarkYellow }
if($ok){ Write-Host '\nBUILD ENVIRONMENT READY' -ForegroundColor Green; exit 0 }
Write-Host '\nBUILD ENVIRONMENT NEEDS ATTENTION' -ForegroundColor Yellow
exit 2
