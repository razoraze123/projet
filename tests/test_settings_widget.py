from pathlib import Path
import sys
import os
import subprocess
import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = QtWidgets.QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from MOTEUR.scraping.widgets.settings_widget import ScrapingSettingsWidget
from MOTEUR.scraping.utils import update


def test_update_button_triggers_git_pull(monkeypatch):
    calls = {}

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    app = QApplication.instance() or QApplication([])
    widget = ScrapingSettingsWidget(show_maintenance=True)
    btn = widget.findChild(QtWidgets.QPushButton, "btn_update")
    btn.click()
    widget.close()

    expected = ["git", "-C", str(update.PROJECT_ROOT), "pull", "origin", "main"]
    assert calls["cmd"] == expected
