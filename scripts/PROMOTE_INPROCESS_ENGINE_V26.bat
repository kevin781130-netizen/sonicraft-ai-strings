@echo off
setlocal
cd /d "%~dp0.."
echo Usage: edit paths below to your REAL production evidence. Synthetic/mock evidence is not valid for commercial promotion.
python training\scripts\build_inprocess_promotion_v26.py ^
  --bundle-evidence release\inprocess_bundle_v26.json ^
  --parity release\inprocess_parity_v26.json ^
  --runtime-abx release\runtime_abx.json ^
  --native-promotion release\native_runtime_promotion_v23.json ^
  --ultra-low-latency-promotion release\ultra_low_latency_promotion_v25.json ^
  --out release\inprocess_neural_promotion_v26.json ^
  --lock release\inprocess_promotion_v26.lock
