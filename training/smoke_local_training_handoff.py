"""Exercise preflight failures and real cmd.exe launcher behavior without a GPU."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv

ROOT = Path(__file__).resolve().parents[1]


class PreflightTests(unittest.TestCase):
    def test_data_outputs_and_custom_pause(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latent = root / 'latent.npz'
            latent.write_bytes(b'path-only fixture; no acoustic evidence')
            index = root / 'index.jsonl'
            index.write_text(json.dumps({'file': str(latent)}) + '\n')
            pause = root / 'pause.json'
            base = [sys.executable, str(ROOT/'training/gpu_training_preflight.py'),
                    '--index', str(index), '--allow-no-cuda', '--json',
                    '--pause-file', str(pause), '--status-file', str(root/'status.json')]
            def check(extra, ok, message=''):
                cp = subprocess.run(base + extra, capture_output=True, text=True)
                report = json.loads(cp.stdout)
                self.assertEqual(cp.returncode, 0 if ok else 2, report)
                self.assertEqual(report['ok'], ok)
                if message:
                    self.assertIn(message, ' '.join(report['errors']))
            check([], True)
            check(['--val-index', str(root/'missing.jsonl')], False, 'validation index')
            check(['--out', str(root)], False, 'not a directory')
            check(['--out', str(root/'same.pt'), '--best-out', str(root/'same.pt')], False, 'different files')
            pause.write_text('{}')
            check([], False, 'pause request')


@unittest.skipUnless(os.name == 'nt', 'requires actual Windows cmd.exe')
class WindowsLauncherTests(unittest.TestCase):
    def test_launchers_use_venv_and_propagate_failures(self):
        # A path with spaces catches quoting bugs. No real model or GUI is used.
        with tempfile.TemporaryDirectory(prefix='sonicraft handoff ') as td:
            root = Path(td)
            (root/'training').mkdir()
            (root/'scripts').mkdir()
            venv.EnvBuilder(with_pip=False).create(root/'.venv')
            for name in ('TRAIN_RENDERER_GPU.bat', 'TRAIN_PERFORMANCE_PLANNER.bat',
                         'PAUSE_TRAINING.bat', 'RESUME_TRAINING.bat', 'TRAINING_CONTROL_PANEL.bat',
                         'scripts/SELECT_TRAINING_PYTHON.bat'):
                shutil.copy2(ROOT/name, root/name)
            stub = '''import json, os, sys
from pathlib import Path
name = Path(__file__).name
Path(name + '.called').write_text(json.dumps({'argv': sys.argv, 'prefix': sys.prefix}))
raise SystemExit(int(os.environ.get('HANDOFF_PREFLIGHT_EXIT' if name == 'gpu_training_preflight.py' else 'HANDOFF_TRAIN_EXIT', '0')))
'''
            for name in ('gpu_training_preflight.py', 'train_ballad_renderer_pausable.py',
                         'train_performance_planner.py', 'training_control.py', 'training_control_panel.py'):
                (root/'training'/name).write_text(stub)
            def run(name, args=(), preflight=0, trainer=0):
                env = dict(os.environ, HANDOFF_PREFLIGHT_EXIT=str(preflight), HANDOFF_TRAIN_EXIT=str(trainer))
                # cmd.exe, not a textual BAT inspection, is the behavior under test.
                command = subprocess.list2cmdline([str(root/name), *args])
                # Pass one cmd command line: Python list quoting uses backslash
                # escapes, which cmd.exe does not understand around BAT paths.
                comspec = os.environ.get('COMSPEC', 'cmd.exe')
                return subprocess.run(f'"{comspec}" /d /s /c "{command}"',
                                      cwd=root, env=env, capture_output=True, text=True, timeout=30)
            args = ['--index', 'data with spaces.jsonl']
            failed = run('TRAIN_RENDERER_GPU.bat', args, preflight=7)
            self.assertEqual(failed.returncode, 2, failed.stdout + failed.stderr)
            self.assertFalse((root/'train_ballad_renderer_pausable.py.called').exists())
            self.assertFalse((root/'training_control_panel.py.called').exists())
            for name, script in [('TRAIN_RENDERER_GPU.bat', 'train_ballad_renderer_pausable.py'),
                                 ('TRAIN_PERFORMANCE_PLANNER.bat', 'train_performance_planner.py')]:
                for code in (0, 7):
                    cp = run(name, args, trainer=code)
                    self.assertEqual(cp.returncode, code, cp.stdout + cp.stderr)
                    called = json.loads((root/(script+'.called')).read_text())
                    self.assertEqual(Path(called['prefix']).resolve(), (root/'.venv').resolve())
                    self.assertEqual(called['argv'][1:], args)
            for name in ('PAUSE_TRAINING.bat', 'RESUME_TRAINING.bat', 'TRAINING_CONTROL_PANEL.bat'):
                cp = run(name, trainer=7)
                self.assertEqual(cp.returncode, 7, cp.stdout + cp.stderr)


if __name__ == '__main__':
    unittest.main()
