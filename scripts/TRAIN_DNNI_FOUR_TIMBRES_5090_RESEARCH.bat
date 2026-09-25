@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0.."
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 echo [INFO] No .venv activated; using current Python.

set ROOT=datasets\dnni_four_timbres
set RAW=%ROOT%\rendered\index.jsonl
if not exist "%RAW%" (
  echo [ERROR] Missing %RAW%
  echo 1. Run: python training\scripts\generate_dnni_capture_plan.py
  echo 2. Render the four DNNI timbres to the expected WAV filenames.
  echo 3. Run: python training\scripts\build_dnni_render_manifest.py
  exit /b 2
)

python -c "import torch; assert torch.cuda.is_available(), 'CUDA GPU not available'; print(torch.cuda.get_device_name(0)); print('bf16',torch.cuda.is_bf16_supported())" || exit /b 2

if not exist checkpoints mkdir checkpoints

echo [1/5] Train research VAE64 timbre codec on four DNNI render lanes.
python training\train_codec.py --manifest "%RAW%" --arch vae64 --width 32 --epochs 100 --batch 4 --real-ratio 1.0 --modeled-ratio 0.0 --modeled-recon-weight 1.0 --physics-weight 0.0 --physics-metric-weight 0.0 --out checkpoints\dnni4_vae64_research.pt --decoder-out checkpoints\dnni4_vae64_decoder_research.pt || exit /b 1

echo [2/5] Encode the capture controls into SONICRAFT VAE64 latents.
python training\scripts\encode_vae64_latents.py --index "%RAW%" --codec checkpoints\dnni4_vae64_research.pt --out %ROOT%\latents || exit /b 1

echo [3/5] Train high-capacity four-timbre renderer on RTX 5090.
python training\scripts\run_dnni_research_entry.py renderer -- --index %ROOT%\latents\index.jsonl --preset hq_strings_v18 --epochs 260 --batch 2 --accum 2 --real-ratio 1.0 --modeled-ratio 0.0 --out checkpoints\dnni4_renderer_hq_research_last.pt --best-out checkpoints\dnni4_renderer_hq_research_best.pt || exit /b 1

echo [4/5] Distill HQ renderer into Frontier Core.
python training\scripts\run_dnni_research_entry.py distill -- --index %ROOT%\latents\index.jsonl --teacher checkpoints\dnni4_renderer_hq_research_best.pt --student-preset frontier_core_dit --epochs 130 --batch 2 --accum 2 --real-ratio 1.0 --modeled-ratio 0.0 --out checkpoints\dnni4_frontier_research.pt || exit /b 1

echo [5/5] Shortcut distillation for low-step inference.
python training\scripts\run_dnni_research_entry.py shortcut -- --index %ROOT%\latents\index.jsonl --init checkpoints\dnni4_frontier_research.pt --preset frontier_core_dit --max-steps 8 --recommend-steps 2 --epochs 55 --batch 1 --accum 1 --real-ratio 1.0 --modeled-ratio 0.0 --out checkpoints\dnni4_frontier_shortcut_research.pt || exit /b 1

echo.
echo [DONE - RESEARCH ONLY]
echo Output: checkpoints\dnni4_frontier_shortcut_research.pt
echo This path does NOT satisfy SONICRAFT commercial clean-room/release gates.
endlocal
