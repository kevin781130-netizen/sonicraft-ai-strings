param([string]$ProjectRoot='',[string]$BuildDir='',[string]$OrtSdkRoot='')
$ErrorActionPreference='Stop'
if(-not $ProjectRoot){$ProjectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path}
$root=(Resolve-Path $ProjectRoot).Path
if(-not $BuildDir){$BuildDir=Join-Path $root 'build\product-shell-v26'}
$args=@('-S',$root,'-B',$BuildDir,'-DSONICRAFT_BUILD_VST3=OFF','-DSONICRAFT_BUILD_PRODUCT_SHELL=ON','-DSONICRAFT_BUILD_INPROCESS_ENGINE=ON')
if($OrtSdkRoot){$args+=('-DSONICRAFT_ORT_SDK_ROOT='+$OrtSdkRoot)}
& cmake @args;if($LASTEXITCODE){throw 'CMake configure failed'}
& cmake --build $BuildDir --config Release --target SonicraftAIStringsProductShell SonicraftAIStringsStandalone SonicraftInProcessEngineSmoke SonicraftInProcessPromotionGuardSmoke --parallel
if($LASTEXITCODE){throw 'Product Shell v2.6 build failed'}
$out=Join-Path $root 'release\ProductShell';New-Item -ItemType Directory -Force -Path $out|Out-Null
foreach($name in @('SonicraftAIStringsProductShell.exe','SonicraftAIStringsStandalone.exe')){$cand=@(Join-Path $BuildDir ('Release\'+$name),Join-Path $BuildDir $name)|Where-Object{Test-Path $_}|Select-Object -First 1;if(-not$cand){throw "Missing built executable: $name"};Copy-Item -Force $cand $out}
Write-Host "PRODUCT SHELL V2.6 BUILT: $out" -ForegroundColor Green
if(-not $OrtSdkRoot){Write-Warning 'Built with service fallback only. Supply -OrtSdkRoot for the native ORT adapter; promotion evidence is still required at runtime.'}
