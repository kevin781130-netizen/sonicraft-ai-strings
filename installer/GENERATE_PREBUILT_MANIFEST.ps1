param([string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),[string]$PrebuiltRoot='')
$ErrorActionPreference='Stop';$root=(Resolve-Path $ProjectRoot).Path;if(-not$PrebuiltRoot){$PrebuiltRoot=Join-Path $root 'release\prebuilt'}
$files=Get-ChildItem $PrebuiltRoot -Recurse -File|Where-Object{$_.Name -ne 'prebuilt_manifest.json'}
$rows=foreach($f in $files){[ordered]@{path=$f.FullName.Substring($PrebuiltRoot.Length+1).Replace('\','/');bytes=$f.Length;sha256=(Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower()}}
[ordered]@{format=1;product='SONICRAFT AI Strings Q4';version='7.0.0-rc2';generated_at=(Get-Date).ToUniversalTime().ToString('o');files=$rows}|ConvertTo-Json -Depth 5|Set-Content -Encoding UTF8 (Join-Path $PrebuiltRoot 'prebuilt_manifest.json')
Write-Host 'prebuilt_manifest.json generated.' -ForegroundColor Green
