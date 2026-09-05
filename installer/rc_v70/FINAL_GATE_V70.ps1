param(
  [string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))),
  [switch]$PublicRelease
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path $ProjectRoot).Path
$py=Get-Command python.exe -ErrorAction SilentlyContinue
if(-not$py){$py=Get-Command py.exe -ErrorAction SilentlyContinue}
if(-not$py){throw 'Python is required for the deterministic v7.0 final gate.'}
$args=@((Join-Path $root 'runtime\release_gate_v70.py'),'--root',$root)
if($PublicRelease){$args+='--public'}
& $py.Source @args
exit $LASTEXITCODE
