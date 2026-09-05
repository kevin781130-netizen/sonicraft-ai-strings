param(
  [string]$ProjectRoot = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
  [string]$Vst3SdkCommit = '9fad9770f2ae8542ab1a548a68c1ad1ac690abe0'
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$EvidenceDir = Join-Path $ProjectRoot 'release\rc_evidence'
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
$Log = Join-Path $EvidenceDir 'windows_vst3_build.log'
if (Test-Path $Log) { Remove-Item -Force $Log }
function Log([string]$m) { $line = "[$(Get-Date -Format s)] $m"; $line | Tee-Object -FilePath $Log -Append }
function Need-Cmd([string]$name) { if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { throw "$name is required." } }
function Run-Git([string[]]$Args) {
  & git @Args
  if ($LASTEXITCODE -ne 0) { throw "git failed: git $($Args -join ' ')" }
}

Log 'SONICRAFT AI Strings Q4 v7.0 RC2 reproducible Windows VST3 build'
Need-Cmd cmake
Need-Cmd git

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path $vswhere)) { throw 'Visual Studio 2022/2026 or Build Tools with Desktop C++ workload is required.' }
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'MSVC x64 build tools were not found.' }
$devcmd = Join-Path $vs 'Common7\Tools\VsDevCmd.bat'
if (-not (Test-Path $devcmd)) { throw "VsDevCmd.bat not found: $devcmd" }

$deps = Join-Path $ProjectRoot '_deps'
$sdk = Join-Path $deps 'vst3sdk'
New-Item -ItemType Directory -Force -Path $deps | Out-Null
if (-not (Test-Path (Join-Path $sdk '.git'))) {
  if (Test-Path $sdk) { Remove-Item -Recurse -Force $sdk }
  Log 'Cloning official Steinberg VST3 SDK repository (dependency cache only)...'
  Run-Git @('clone','--filter=blob:none','--no-checkout','https://github.com/steinbergmedia/vst3sdk.git',$sdk)
}
Log "Pinning Steinberg VST3 SDK to $Vst3SdkCommit"
Run-Git @('-C',$sdk,'fetch','--depth','1','origin',$Vst3SdkCommit)
Run-Git @('-C',$sdk,'checkout','--detach','--force',$Vst3SdkCommit)
Run-Git @('-C',$sdk,'submodule','sync','--recursive')
Run-Git @('-C',$sdk,'submodule','update','--init','--recursive','--depth','1')
$actualSdkCommit = (& git -C $sdk rev-parse HEAD).Trim()
if ($actualSdkCommit.ToLowerInvariant() -ne $Vst3SdkCommit.ToLowerInvariant()) { throw "VST3 SDK pin mismatch: $actualSdkCommit" }
$sdkCmake = Get-Content (Join-Path $sdk 'CMakeLists.txt') -Raw
if ($sdkCmake -notmatch 'VERSION\s+3\.8\.0') { throw 'Pinned VST3 SDK no longer reports expected SDK 3.8.0.' }

$build = Join-Path $ProjectRoot 'build-win64-v70'
if (Test-Path $build) { Remove-Item -Recurse -Force $build }
New-Item -ItemType Directory -Force -Path $build | Out-Null
$cfg = "`"$devcmd`" -arch=x64 -host_arch=x64 >nul && cmake -S `"$ProjectRoot`" -B `"$build`" -G `"Visual Studio 17 2022`" -A x64 -DVST3_SDK_ROOT=`"$sdk`" -DSMTG_CREATE_PLUGIN_LINK=0 -DSMTG_PLUGIN_TARGET_USER_PROGRAM_FILES_COMMON=1 -DSMTG_ENABLE_VST3_PLUGIN_EXAMPLES=OFF -DSMTG_ENABLE_VST3_HOSTING_EXAMPLES=ON"
Log 'Configuring pinned VST3 SDK + VSTGUI release project...'
cmd.exe /d /s /c $cfg 2>&1 | Tee-Object -FilePath $Log -Append | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'CMake configure failed.' }

$buildCmd = "`"$devcmd`" -arch=x64 -host_arch=x64 >nul && cmake --build `"$build`" --config Release --target SonicraftAIStringsQ4 --parallel"
Log 'Building SONICRAFT VST3 Release x64...'
cmd.exe /d /s /c $buildCmd 2>&1 | Tee-Object -FilePath $Log -Append | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'VST3 Release build failed.' }

$bundle = Get-ChildItem -Path $build -Recurse -Directory -Filter '*.vst3' | Where-Object { $_.Name -match 'SonicraftAIStringsQ4' } | Select-Object -First 1
if (-not $bundle) { throw 'Build succeeded but VST3 bundle was not found.' }
$release = Join-Path $ProjectRoot 'release'
$dest = Join-Path $release 'SONICRAFT AI Strings Q4.vst3'
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
Copy-Item -Recurse -Force $bundle.FullName $dest
$pluginBinary = Get-ChildItem (Join-Path $dest 'Contents\x86_64-win') -File -Filter '*.vst3' | Select-Object -First 1
if (-not $pluginBinary) { throw 'Built bundle has no x86_64-win VST3 binary.' }
$pluginHash = (Get-FileHash $pluginBinary.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
Log "VST3 bundle ready: $dest"
Log "VST3 binary SHA-256: $pluginHash"

Log 'Building official Steinberg validator from the SAME pinned SDK...'
$valCmd = "`"$devcmd`" -arch=x64 -host_arch=x64 >nul && cmake --build `"$build`" --config Release --target validator --parallel"
cmd.exe /d /s /c $valCmd 2>&1 | Tee-Object -FilePath $Log -Append | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Official VST3 validator build failed.' }
$validator = Get-ChildItem -Path $build -Recurse -File -Filter 'validator.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $validator) { throw 'Official VST3 validator executable was not found.' }
$validatorHash = (Get-FileHash $validator.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$validatorLog = Join-Path $EvidenceDir 'steinberg_validator.log'
Log "Running official validator: $($validator.FullName)"
& $validator.FullName $dest 2>&1 | Tee-Object -FilePath $validatorLog | Out-Host
$validatorExit = $LASTEXITCODE
$validatorPassed = ($validatorExit -eq 0)
$validatorEvidence = [ordered]@{
  schema = 1
  product = 'SONICRAFT AI Strings Q4'
  release = '7.0.0-rc2'
  passed = $validatorPassed
  validated_at = (Get-Date).ToUniversalTime().ToString('o')
  vst3_bundle = $dest
  vst3_binary = $pluginBinary.Name
  vst3_sha256 = $pluginHash
  validator_path = $validator.FullName
  validator_sha256 = $validatorHash
  validator_exit_code = $validatorExit
  vst3_sdk_version = '3.8.0'
  vst3_sdk_commit = $actualSdkCommit
  log = $validatorLog
}
$validatorEvidence | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 (Join-Path $EvidenceDir 'validator-pass.json')
if (-not $validatorPassed) { throw 'VST3 validator reported a failure.' }

$cmakeVersion = (& cmake --version | Select-Object -First 1)
$gitVersion = (& git --version)
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$buildEvidence = [ordered]@{
  schema = 1
  product = 'SONICRAFT AI Strings Q4'
  release = '7.0.0-rc2'
  core_baseline = '6.2.0-acoustic-runtime-provenance'
  frontend_baseline = '6.4.0-frontend-final-candidate'
  status = 'PASS'
  built_at = (Get-Date).ToUniversalTime().ToString('o')
  machine = $env:COMPUTERNAME
  os = [ordered]@{caption=$os.Caption; version=$os.Version; build=$os.BuildNumber}
  cpu = [ordered]@{name=$cpu.Name; architecture=$cpu.Architecture}
  visual_studio_root = $vs
  cmake = $cmakeVersion
  git = $gitVersion
  generator = 'Visual Studio 17 2022 / x64 / Release'
  vst3_sdk = [ordered]@{version='3.8.0'; commit=$actualSdkCommit; source='https://github.com/steinbergmedia/vst3sdk'}
  artifact = [ordered]@{bundle=$dest; binary=$pluginBinary.Name; sha256=$pluginHash}
  validator = [ordered]@{passed=$true; sha256=$validatorHash; evidence='validator-pass.json'}
}
$buildEvidence | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $EvidenceDir 'build-provenance.json')
Copy-Item -Force (Join-Path $EvidenceDir 'validator-pass.json') (Join-Path $ProjectRoot 'release\validator-pass.json')
Write-Host "READY: $dest" -ForegroundColor Green
Write-Host "PINNED SDK: $actualSdkCommit" -ForegroundColor Green
Write-Host "VALIDATOR: PASS" -ForegroundColor Green
