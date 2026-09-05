param([string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)))
$ErrorActionPreference='Stop'
$ProjectRoot=(Resolve-Path $ProjectRoot).Path
$setup=Join-Path $ProjectRoot 'SONICRAFT_AI_Strings_Setup.exe'
$vst=Join-Path $ProjectRoot 'release\SONICRAFT AI Strings Q4.vst3'
if(-not (Test-Path $setup)){throw 'Base Setup.exe not found.'}
if(-not (Test-Path $vst)){throw 'Prebuilt release VST3 not found. Build it first.'}
$marker=[Text.Encoding]::ASCII.GetBytes(('SC_PAYLOAD_ZIP_'+'V09'))
$b=[IO.File]::ReadAllBytes($setup)
$idx=-1
for($i=$b.Length-$marker.Length;$i -ge 0;$i--){$ok=$true;for($j=0;$j -lt $marker.Length;$j++){if($b[$i+$j] -ne $marker[$j]){$ok=$false;break}};if($ok){$idx=$i;break}}
if($idx -lt 0){throw 'SFX marker not found.'}
$stub=New-Object byte[] $idx;[Array]::Copy($b,0,$stub,0,$idx)
$tmp=Join-Path $env:TEMP ('SONICRAFT_REPACK_'+$PID);$zip=$tmp+'.zip'
New-Item -ItemType Directory -Force -Path $tmp|Out-Null
$exclude=@('SONICRAFT_AI_Strings_Setup.exe','_deps','build-win64','build')
Get-ChildItem $ProjectRoot | Where-Object {$exclude -notcontains $_.Name} | ForEach-Object {Copy-Item -Recurse -Force $_.FullName $tmp}
Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $zip -CompressionLevel Optimal -Force
$payload=[IO.File]::ReadAllBytes($zip)
$out=Join-Path $ProjectRoot 'SONICRAFT_AI_Strings_Setup_PREBUILT.exe'
$fs=[IO.File]::Open($out,[IO.FileMode]::Create);try{$fs.Write($stub,0,$stub.Length);$fs.Write($marker,0,$marker.Length);$fs.Write($payload,0,$payload.Length)}finally{$fs.Dispose()}
Remove-Item -Recurse -Force $tmp;Remove-Item -Force $zip
Write-Host "Consumer-ready prebuilt Setup: $out" -ForegroundColor Green
