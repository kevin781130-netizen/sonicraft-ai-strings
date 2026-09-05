@echo off
setlocal
cd /d "%~dp0.."
python training\scripts\build_ultra_low_latency_promotion_v25.py --product-promotion build\realtime_product_promotion_v24.json --latency-benchmark build\ultra_low_latency_v25.json --out build\ultra_low_latency_promotion_v25.json
