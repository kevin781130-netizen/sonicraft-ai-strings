param([string]$Destination=(Join-Path $env:LOCALAPPDATA 'SONICRAFT\AI Strings Q4\Models'))
$ErrorActionPreference='Stop'
$Url='https://github.com/descriptinc/descript-audio-codec/releases/download/1.0.0/weights_44khz_16kbps.pth'
$ExpectedBytes=256984809
New-Item -ItemType Directory -Force -Path $Destination|Out-Null
$Out=Join-Path $Destination 'weights_44khz_16kbps.pth'
Write-Host 'Downloading pinned Descript DAC 44.1kHz / 16kbps base weight v1.0.0...' -ForegroundColor Cyan
Invoke-WebRequest -Uri $Url -OutFile $Out -UseBasicParsing
if((Get-Item $Out).Length -ne $ExpectedBytes){Remove-Item -Force $Out;throw 'DAC base download size mismatch; file removed.'}
$h=(Get-FileHash $Out -Algorithm SHA256).Hash.ToLower()
Write-Host "Downloaded: $Out"
Write-Host "SHA-256: $h"
Write-Host 'The final commercial model-manifest builder will pin this exact SHA-256 together with the fine-tuned decoder and HQ model.' -ForegroundColor Green
