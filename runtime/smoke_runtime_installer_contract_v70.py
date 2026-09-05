from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1']:
    s=(ROOT/rel).read_text(encoding='utf-8',errors='ignore')
    assert 'Python.Python.3.11' in s, f'{rel}: Python 3.11 bootstrap missing'
    assert '(3,11) <= sys.version_info[:2] < (3,14)' in s, f'{rel}: compatible Python range gate missing'
    assert 'Python.Python.3.10' not in s and 'Python310' not in s, f'{rel}: stale Python 3.10 bootstrap remains'
    assert 'onnxruntime==1.29.0' in s, f'{rel}: ORT pin missing'
    assert 'torch==2.8.0' in s and '/whl/cu128' in s, f'{rel}: Torch/CUDA pin missing'
    assert 'not(Compatible-Python $VenvPy)' in s and 'Remove-Item -Recurse -Force $Venv' in s, f'{rel}: incompatible old venv is not rebuilt'
collect=(ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text(encoding='utf-8',errors='ignore')
assert 'INSTALL_AI_RUNTIME_RELEASE.ps1' in collect
print('SONICRAFT v7.0 runtime installer compatibility contract PASS')
print(' Python: 3.11-3.13')
print(' ONNX Runtime: 1.29.0')
print(' PyTorch: 2.8.0 / CUDA 12.8')
print(' Old incompatible venv migration: PASS')
