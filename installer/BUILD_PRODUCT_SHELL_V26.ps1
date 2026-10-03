param([string]$ProjectRoot='',[string]$BuildDir='',[string]$OrtSdkRoot='')
$ErrorActionPreference='Stop'
if(-not $ProjectRoot){$ProjectRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path}
$root=(Resolve-Path $ProjectRoot).Path
if(-not $BuildDir){$BuildDir=Join-Path $root 'build\product-shell-v26'}
if(Test-Path $BuildDir){Remove-Item -Recurse -Force $BuildDir}
New-Item -ItemType Directory -Force -Path $BuildDir|Out-Null
$args=@('-S',$root,'-B',$BuildDir,'-G','Visual Studio 17 2022','-A','x64','-DSONICRAFT_BUILD_VST3=OFF','-DSONICRAFT_BUILD_PRODUCT_SHELL=ON','-DSONICRAFT_BUILD_INPROCESS_ENGINE=ON')
if($OrtSdkRoot){$args+=('-DSONICRAFT_ORT_SDK_ROOT='+$OrtSdkRoot)}
& cmake @args;if($LASTEXITCODE){throw 'CMake configure failed'}

# Build each Windows target deterministically. On some local VS 2022 Build Tools
# installations a parallel multi-target build can reach LINK while a freshly
# produced .obj is temporarily unavailable (LNK1104). Keep MSBuild node reuse
# off, serialize targets, and retry the individual target once so a transient
# filesystem/AV lock does not force the operator to restart the entire RC build.
$env:MSBUILDDISABLENODEREUSE='1'
function Build-Target([string]$Target){
  for($attempt=1;$attempt -le 2;$attempt++){
    Write-Host ("Building {0} (attempt {1}/2, serial MSBuild)..." -f $Target,$attempt) -ForegroundColor Cyan
    & cmake --build $BuildDir --config Release --target $Target --parallel 1 -- /nodeReuse:false
    if($LASTEXITCODE -eq 0){return}
    if($attempt -lt 2){
      Write-Warning ("{0} build failed once; retrying after transient-file-lock cooldown." -f $Target)
      Start-Sleep -Seconds 3
    }
  }
  throw ("Product Shell v2.6 target failed after serial retry: {0}" -f $Target)
}
foreach($target in @('SonicraftAIStringsProductShell','SonicraftAIStringsScoreEditor','SonicraftAIStringsStandalone','SonicraftHostQaFeatureSmokeV70','SonicraftInProcessEngineSmoke','SonicraftInProcessPromotionGuardSmoke')){
  Build-Target $target
}
$out=Join-Path $root 'release\ProductShell';New-Item -ItemType Directory -Force -Path $out|Out-Null
foreach($name in @('SonicraftAIStringsProductShell.exe','SonicraftAIStringsScoreEditor.exe','SonicraftAIStringsStandalone.exe')){
  $candidates=@(
    (Join-Path $BuildDir ('Release\'+$name))
    (Join-Path $BuildDir $name)
  )
  $cand=$candidates|Where-Object{Test-Path $_ -PathType Leaf}|Select-Object -First 1
  if(-not$cand){throw "Missing built executable: $name"}
  Copy-Item -Force $cand $out
}
Write-Host "PRODUCT SHELL V2.6 BUILT: $out" -ForegroundColor Green
if(-not $OrtSdkRoot){Write-Warning 'Built with service fallback only. Supply -OrtSdkRoot for the native ORT adapter; promotion evidence is still required at runtime.'}
