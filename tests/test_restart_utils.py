import os
import sys
import subprocess
import time

from MOTEUR.scraping.utils.restart import relaunch_current_process


def test_relaunch_uses_absolute_script_path(monkeypatch, tmp_path):
    # simulate a script launched with a relative path
    script = tmp_path / "script.py"
    script.write_text("print('hi')\n")
    monkeypatch.setattr(sys, 'argv', [script.name, 'arg1'])

    called = {}
    def fake_popen(argv, **kwargs):
        called['argv'] = argv
        class Dummy: pass
        return Dummy()

    monkeypatch.setattr(subprocess, 'Popen', fake_popen)
    monkeypatch.setattr(time, 'sleep', lambda s: None)

    relaunch_current_process()

    assert os.path.isabs(called['argv'][1])
    assert called['argv'][1].endswith('script.py')
