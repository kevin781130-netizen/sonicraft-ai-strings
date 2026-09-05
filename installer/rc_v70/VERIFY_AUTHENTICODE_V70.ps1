param([string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))))
$ErrorActionPreference='Stop';$root=(Resolve-Path $ProjectRoot).Path;$ev=Join-Path $root 'release\rc_evidence';New-Item -ItemType Directory -Force -Path $ev|Out-Null
$bundle=Join-Path $root 'release\SONICRAFT AI Strings Q4.vst3';$bin=Get-ChildItem (Join-Path $bundle 'Contents\x86_64-win') -File -Filter '*.vst3'|Select-Object -First 1
if(-not$bin){throw 'VST3 binary missing'}
$sig=Get-AuthenticodeSignature $bin.FullName
$r=[ordered]@{schema=1;release='7.0.0-rc2';checked_at=(Get-Date).ToUniversalTime().ToString('o');status=$sig.Status.ToString();subject=if($sig.SignerCertificate){$sig.SignerCertificate.Subject}else{''};thumbprint=if($sig.SignerCertificate){$sig.SignerCertificate.Thumbprint}else{''};plugin_sha256=(Get-FileHash $bin.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
$r|ConvertTo-Json -Depth 6|Set-Content -Encoding UTF8 (Join-Path $ev 'authenticode-pass.json')
$r|ConvertTo-Json -Depth 6
if($sig.Status -ne 'Valid'){exit 2}
