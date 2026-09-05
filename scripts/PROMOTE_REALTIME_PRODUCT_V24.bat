@echo off
setlocal
cd /d "%~dp0.."
python training\scripts\build_product_shell_promotion_v24.py --native-promotion release\native_runtime_promotion_v23.json --realtime-benchmark release\realtime_preview_benchmark_v24.json --shell-bundle release\product_shell_bundle_v24.json --out release\realtime_product_promotion_v24.json %*
endlocal
