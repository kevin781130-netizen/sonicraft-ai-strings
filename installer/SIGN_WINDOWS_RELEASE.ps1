param(
  [Parameter(Mandatory=$true)][string]$PfxPath,
  [Parameter(Mandatory=$true)][string]$Password,
  [string]$TimestampUrl='http://timestamp.digicert.com',
  [string]$SetupPath=''
)
$ErrorActionPreference='Stop'; $signtool=(Get-Command signtool.exe -ErrorAction SilentlyContinue).Source
if(-not $signtool){throw 'signtool.exe not found. Install Windows SDK signing tools.'}
$Root=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$targets=@((Join-Path $Root 'SONICRAFT_AI_Strings_Manager.exe'),(Join-Path $Root 'SONICRAFT_AI_Renderer_Service.exe'))
$vst=Join-Path $Root 'release\SONICRAFT AI Strings Q4.vst3'; if(Test-Path $vst){$targets += Get-ChildItem $vst -Recurse -File | Where-Object {$_.Extension -in '.vst3','.dll','.exe'} | ForEach-Object {$_.FullName}}
if($SetupPath){$targets += $SetupPath}else{$targets += (Join-Path $Root 'SONICRAFT_AI_Strings_Setup.exe')}
$targets=$targets|Where-Object {$_ -and (Test-Path $_)}|Select-Object -Unique
foreach($t in $targets){
 & $signtool sign /f $PfxPath /p $Password /fd SHA256 /tr $TimestampUrl /td SHA256 $t
 if($LASTEXITCODE -ne 0){throw "Signing failed: $t"}
 & $signtool verify /pa /v $t; if($LASTEXITCODE -ne 0){throw "Signature verification failed: $t"}
}
Write-Host "Authenticode SHA-256 signing PASS ($($targets.Count) files)." -ForegroundColor Green
