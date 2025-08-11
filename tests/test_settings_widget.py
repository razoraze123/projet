from pathlib import Path
import sys
import os
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
    started = {}

    app = QApplication.instance() or QApplication([])
    widget = ScrapingSettingsWidget(show_maintenance=True)

    def fake_start(program, arguments):
        started["program"] = program
        started["arguments"] = list(arguments)

    def fake_waitForStarted(timeout):
        return True

    monkeypatch.setattr(widget._git_proc, "start", fake_start)
    monkeypatch.setattr(widget._git_proc, "waitForStarted", fake_waitForStarted)

    btn = widget.findChild(QtWidgets.QPushButton, "btn_update")
    btn.click()
    widget.close()

    assert started["program"] == "git"
    assert started["arguments"] == ["pull", "origin", "main"]
    assert widget._git_proc.workingDirectory() == str(update.PROJECT_ROOT)
