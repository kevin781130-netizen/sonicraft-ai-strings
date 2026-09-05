param([string]$ProjectRoot='',[string]$BuildDir='')
$ErrorActionPreference='Stop'
if(-not $ProjectRoot){$ProjectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path}
$root=(Resolve-Path $ProjectRoot).Path
if(-not $BuildDir){$BuildDir=Join-Path $root 'build\product-shell-v25'}
$cm=Get-Command cmake -ErrorAction Stop
& $cm.Source -S $root -B $BuildDir -DSONICRAFT_BUILD_VST3=OFF -DSONICRAFT_BUILD_PRODUCT_SHELL=ON -DSONICRAFT_BUILD_ORT_INPROCESS_PROBE=ON
if($LASTEXITCODE){throw 'CMake configure failed'}
& $cm.Source --build $BuildDir --config Release --target SonicraftAIStringsProductShell SonicraftAIStringsStandalone SonicraftOrtInProcessProbe --parallel
if($LASTEXITCODE){throw 'Product Shell v2.5 build failed'}
$out=Join-Path $root 'release\ProductShell';New-Item -ItemType Directory -Force -Path $out|Out-Null
foreach($name in @('SonicraftAIStringsProductShell.exe','SonicraftAIStringsStandalone.exe','SonicraftOrtInProcessProbe.exe')){$cand=@(Join-Path $BuildDir ('Release\'+$name),Join-Path $BuildDir $name)|Where-Object{Test-Path $_}|Select-Object -First 1;if(-not$cand){throw "Missing built executable: $name"};Copy-Item -Force $cand $out}
Write-Host "PRODUCT SHELL V2.5 BUILT: $out" -ForegroundColor Green
