param([string]$ProjectRoot='',[string]$AppDir='',[ValidateSet('auto','torch','ort')][string]$RuntimeBackend='auto',[string]$OrtWheel='')
$ErrorActionPreference='Stop'
if(-not $AppDir){$AppDir = if($env:SONICRAFT_AI_STRINGS_HOME){$env:SONICRAFT_AI_STRINGS_HOME}else{Join-Path $env:LOCALAPPDATA 'SONICRAFT\AI Strings Q4'}}
$Runtime = Join-Path $AppDir 'Runtime'
$ModelDir = Join-Path $AppDir 'Models'; New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null
$RoomDir = Join-Path $AppDir 'Room'; New-Item -ItemType Directory -Force -Path $RoomDir | Out-Null
$Source = if($ProjectRoot){$ProjectRoot}else{Join-Path $AppDir 'Source-v1.2-RC2'}
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null

function Run([string]$Exe,[string[]]$Args,[string]$What){
  & $Exe @Args
  if($LASTEXITCODE -ne 0){ throw "$What failed with exit code $LASTEXITCODE" }
}

function Compatible-Python([string]$Exe){
  if(-not $Exe -or -not(Test-Path $Exe -PathType Leaf -ErrorAction SilentlyContinue)){return $false}
  & $Exe -c "import sys; raise SystemExit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 3)" 2>$null
  return ($LASTEXITCODE -eq 0)
}
$Py=$null
$existing=Get-Command python.exe -ErrorAction SilentlyContinue
if($existing -and (Compatible-Python $existing.Source)){$Py=$existing}
if(-not $Py){
  $cand=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
  if(Compatible-Python $cand){$Py=[pscustomobject]@{Source=$cand}}
}
if(-not $Py){
  $winget=Get-Command winget.exe -ErrorAction SilentlyContinue
  if(-not $winget){throw 'Python 3.11-3.13 is required and winget was not found.'}
  & winget install --id Python.Python.3.11 -e --scope user --accept-package-agreements --accept-source-agreements
  if($LASTEXITCODE -ne 0){throw 'Python 3.11 installation failed.'}
  $cand=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
  if(Compatible-Python $cand){$Py=[pscustomobject]@{Source=$cand}}
}
if(-not $Py){throw 'Compatible Python 3.11-3.13 executable still not found.'}
$Venv = Join-Path $Runtime 'venv'
$VenvPy=Join-Path $Venv 'Scripts\python.exe'
if((Test-Path $VenvPy) -and -not(Compatible-Python $VenvPy)){Remove-Item -Recurse -Force $Venv}
if(-not(Test-Path $VenvPy)){ Run $Py.Source @('-m','venv',$Venv) 'Python venv creation' }
$VPy=$VenvPy
Run $VPy @('-m','pip','install','--upgrade','pip','wheel') 'pip bootstrap'
Run $VPy @('-m','pip','install','numpy>=2.0,<3','soundfile==0.14.0','protobuf>=4.25,<6') 'base runtime dependencies'
$EffectiveBackend=$RuntimeBackend
if($EffectiveBackend -eq 'auto'){
  $selFile=Join-Path $Source 'runtime\runtime_backend_selector_v24.py'
  if(Test-Path $selFile){
    $selDir=(Split-Path $selFile -Parent).Replace('\','\\');$appEsc=$AppDir.Replace('\','\\');$modelEsc=$ModelDir.Replace('\','\\')
    $code="import sys;sys.path.insert(0,r'$selDir');from runtime_backend_selector_v24 import select_backend;print(select_backend(r'$appEsc',r'$modelEsc','auto')[0])"
    try{$choice=(& $VPy -c $code 2>$null|Out-String).Trim();if($choice -in @('torch','ort')){$EffectiveBackend=$choice}else{$EffectiveBackend='torch'}}catch{$EffectiveBackend='torch'}
  }else{$EffectiveBackend='torch'}
}
if($EffectiveBackend -eq 'ort'){
  # v2.2 no-PyTorch challenger. A supplied custom wheel is the production-size candidate;
  # PyPI ORT remains a validation bridge until native-runtime promotion evidence passes.
  if($OrtWheel){if(-not(Test-Path $OrtWheel)){throw "ORT wheel not found: $OrtWheel"};Run $VPy @('-m','pip','install',$OrtWheel) 'Reduced ONNX Runtime wheel'}
  else{Run $VPy @('-m','pip','install','onnxruntime==1.29.0') 'ONNX Runtime CPU bridge'}
}else{
  # Proven acoustic path stays default until ORT numerical/ABX promotion evidence passes.
  $hasNvidia=$false; if(Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue){$hasNvidia=$true}
  if($hasNvidia){Run $VPy @('-m','pip','install','torch==2.8.0','--index-url','https://download.pytorch.org/whl/cu128') 'PyTorch CUDA runtime'}else{Run $VPy @('-m','pip','install','torch==2.8.0','--index-url','https://download.pytorch.org/whl/cpu') 'PyTorch CPU runtime'}
}
# v1.6 VAE64 has no DAC package dependency. Install DAC only when an already-selected legacy model pack requires it.
$needDac=$false; $mp=Join-Path $ModelDir 'release_model_manifest.json'; if(Test-Path $mp){try{$mm=Get-Content $mp -Raw|ConvertFrom-Json;$needDac=(-not $mm.codec -or ([string]$mm.codec.kind).ToLower() -ne 'strings_vae64')}catch{}}
if($needDac){Run $VPy @('-m','pip','install','descript-audio-codec==1.0.0') 'Legacy Descript DAC runtime'}

# Copy the complete runtime, not only the launcher, so the installed runtime is self-contained
# even if Source-v1.2-RC2 is later removed to save disk space.
foreach($name in @('renderer_service_launcher.ps1','renderer_service.py','audio_take_judge_v37.py','judge_memory_v38.py','score_expression_graph_v40.py','compile_musicxml_strings_v41.py','compile_musicxml_strings_v42.py','string_physical_graph_v42.py','string_physical_runtime_v42.py','string_constraint_solver_v43.py','compile_musicxml_strings_v43.py','string_ensemble_solver_v44.py','string_ensemble_runtime_v44.py','compile_musicxml_strings_v44.py','string_gesture_graph_v45.py','string_gesture_runtime_v45.py','compile_musicxml_strings_v45.py','string_transition_graph_v46.py','string_transition_runtime_v46.py','compile_musicxml_strings_v46.py','string_phrase_longline_v47.py','string_phrase_runtime_v47.py','compile_musicxml_strings_v47.py','string_performance_critic_v48.py','compile_musicxml_strings_v48.py','string_repair_policy_v49.py','audio_io_v49.py','midi_judge_adapter_v49.py','compile_musicxml_strings_v49.py','iterate_strings_v49.py','shadow_render_auto_v50.py','compile_musicxml_strings_v50.py','auto_loop_strings_v50.py','selective_phrase_search_v51.py','shadow_render_selective_v51.py','selective_midi_merge_v51.py','compile_musicxml_strings_v51.py','auto_loop_strings_v51.py','global_performance_coherence_v52.py','compile_musicxml_strings_v52.py','auto_loop_strings_v52.py','conductor_intent_v53.py','compile_musicxml_strings_v53.py','auto_loop_strings_v53.py','conductor_candidate_steering_v54.py','compile_musicxml_strings_v54.py','auto_loop_strings_v54.py','candidate_utility_predictor_v55.py','compile_musicxml_strings_v55.py','auto_loop_strings_v55.py','counterfactual_auditor_v56.py','compile_musicxml_strings_v56.py','auto_loop_strings_v56.py','context_similarity_transfer_v57.py','compile_musicxml_strings_v57.py','auto_loop_strings_v57.py','performance_archetype_memory_v58.py','compile_musicxml_strings_v58.py','auto_loop_strings_v58.py','archetype_mixture_v59.py','compile_musicxml_strings_v59.py','auto_loop_strings_v59.py','evidence_store_v60.py','compile_musicxml_strings_v60.py','auto_loop_strings_v60.py','performance_checkpoint_v61.py','compile_musicxml_strings_v61.py','auto_loop_strings_v61.py','acoustic_runtime_provenance_v62.py','performance_checkpoint_v62.py','compile_musicxml_strings_v62.py','auto_loop_strings_v62.py','compile_midi_performance_v29.py','model_backend.py','release_integrity.py','flow_sampler.py','quartet_interaction.py','frontier_context.py','tile_cache.py','instrument_x_cleanroom.py','polyphony.py','stage_renderer.py','stage_renderer_np.py','control_builder_np.py','ort_model_backend.py','runtime_backend_selector_v24.py','musicxml_import.py','protocol.py','status_client.py','smoke_client.py')){
  $p=Join-Path $Source ('runtime\'+$name); if(-not(Test-Path $p)){throw "Runtime file missing: $p"}; Copy-Item -Force $p $Runtime
}
$ModelCode=Join-Path $Runtime 'models'; New-Item -ItemType Directory -Force -Path $ModelCode|Out-Null
foreach($name in @('__init__.py','adaptive_flow_dit.py','ballad_flow_renderer.py','vibrato_expert.py','performance_experts.py','string_vae64.py')){
  $p=Join-Path $Source ('runtime\models\'+$name); if(-not(Test-Path $p)){$p=Join-Path $Source ('training\models\'+$name)}; if(Test-Path $p){Copy-Item -Force $p $ModelCode}
}
$svc = Join-Path $Source 'SONICRAFT_AI_Renderer_Service.exe'
if(Test-Path $svc){Copy-Item -Force $svc $Runtime}

# Import test catches broken binary wheels / ABI mismatches before Manager reports READY.
$probe=@'
import numpy, soundfile
import model_backend, ort_model_backend, control_builder_np, stage_renderer_np, instrument_x_cleanroom, polyphony, stage_renderer, musicxml_import, score_expression_graph_v40, compile_musicxml_strings_v41, compile_musicxml_strings_v42, string_physical_graph_v42, string_physical_runtime_v42, string_constraint_solver_v43, compile_musicxml_strings_v43, string_ensemble_solver_v44, string_ensemble_runtime_v44, compile_musicxml_strings_v44, string_gesture_graph_v45, string_gesture_runtime_v45, compile_musicxml_strings_v45, string_transition_graph_v46, string_transition_runtime_v46, compile_musicxml_strings_v46, string_phrase_longline_v47, string_phrase_runtime_v47, compile_musicxml_strings_v47, string_performance_critic_v48, compile_musicxml_strings_v48, string_repair_policy_v49, audio_io_v49, midi_judge_adapter_v49, compile_musicxml_strings_v49, iterate_strings_v49, shadow_render_auto_v50, compile_musicxml_strings_v50, auto_loop_strings_v50, selective_phrase_search_v51, shadow_render_selective_v51, selective_midi_merge_v51, compile_musicxml_strings_v51, auto_loop_strings_v51, global_performance_coherence_v52, compile_musicxml_strings_v52, auto_loop_strings_v52, conductor_intent_v53, compile_musicxml_strings_v53, auto_loop_strings_v53, conductor_candidate_steering_v54, compile_musicxml_strings_v54, auto_loop_strings_v54, candidate_utility_predictor_v55, compile_musicxml_strings_v55, auto_loop_strings_v55, counterfactual_auditor_v56, compile_musicxml_strings_v56, auto_loop_strings_v56, context_similarity_transfer_v57, compile_musicxml_strings_v57, auto_loop_strings_v57, performance_archetype_memory_v58, compile_musicxml_strings_v58, auto_loop_strings_v58, archetype_mixture_v59, compile_musicxml_strings_v59, auto_loop_strings_v59, evidence_store_v60, compile_musicxml_strings_v60, auto_loop_strings_v60, performance_checkpoint_v61, compile_musicxml_strings_v61, auto_loop_strings_v61, compile_midi_performance_v29
print('numpy', numpy.__version__); print('soundfile', soundfile.__version__)
try:
 import torch; from models.ballad_flow_renderer import BalladFlowRenderer; from models.string_vae64 import StringVAE64Decoder; print('torch',torch.__version__,'cuda',torch.cuda.is_available())
except ImportError:
 import onnxruntime as ort; print('onnxruntime',ort.__version__)
print('fallback runtime modules PASS')
'@
$probePath=Join-Path $Runtime '_runtime_import_probe.py'; $probe | Set-Content -Encoding UTF8 $probePath
Run $VPy @($probePath) 'AI runtime import verification'
Remove-Item -Force $probePath -ErrorAction SilentlyContinue

$runKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
New-Item -Force $runKey | Out-Null
$svcInstalled=Join-Path $Runtime 'SONICRAFT_AI_Renderer_Service.exe'
if(Test-Path $svcInstalled){
  New-ItemProperty -Path $runKey -Name 'SONICRAFT_AI_Renderer_Service' -Value ('"'+$svcInstalled+'"') -PropertyType String -Force | Out-Null
  Start-Process $svcInstalled
}
Write-Host 'AI Runtime installed and import-verified.' -ForegroundColor Green
