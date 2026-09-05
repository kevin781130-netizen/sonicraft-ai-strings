param([string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),[string]$BuildDir='')
$ErrorActionPreference='Stop';$root=(Resolve-Path $ProjectRoot).Path;if(-not$BuildDir){$BuildDir=Join-Path $root 'build\product-shell-v24'}
$cm=Get-Command cmake.exe -ErrorAction SilentlyContinue;if(-not$cm){throw 'CMake is required.'}
& $cm.Source -S $root -B $BuildDir -DSONICRAFT_BUILD_VST3=OFF -DSONICRAFT_BUILD_STANDALONE=ON -DSONICRAFT_BUILD_REALTIME_SIM=OFF -DSONICRAFT_BUILD_PRODUCT_SHELL=ON
if($LASTEXITCODE -ne 0){throw 'Product Shell configure failed.'}
& $cm.Source --build $BuildDir --config Release --target SonicraftAIStringsProductShell SonicraftAIStringsStandalone --parallel
if($LASTEXITCODE -ne 0){throw 'Product Shell build failed.'}
$out=Join-Path $root 'release\ProductShell';New-Item -ItemType Directory -Force -Path $out|Out-Null
foreach($name in @('SonicraftAIStringsProductShell.exe','SonicraftAIStringsStandalone.exe')){$cand=@(Join-Path $BuildDir ('Release\'+$name),Join-Path $BuildDir $name)|Where-Object{Test-Path $_}|Select-Object -First 1;if(-not$cand){throw "Missing built executable: $name"};Copy-Item -Force $cand $out}
Write-Host "PRODUCT SHELL V2.4 BUILT: $out" -ForegroundColor Green
