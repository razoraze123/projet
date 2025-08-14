# localapp/pages/settings_page.py
from pathlib import Path
import os, sys
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QLabel,
    QCheckBox,
    QGroupBox,
)
from PySide6.QtCore import QProcess, Qt
from localapp.utils_collect import detect_project_root, build_copy_txt
try:
    from localapp.ui_animations import toast
except Exception:
    toast = lambda *a, **k: None

class SettingsPage(QWidget):
    def __init__(self, app_ctx, parent=None):
        """
        app_ctx: objet contenant au moins:
          - root_dir (Path): racine du projet (cwd du git pull)
          - apply_theme(theme: str): applique 'dark' ou 'light' à l'app et persiste dans settings.json
          - current_theme() -> str: retourne 'dark' ou 'light'
          - log(msg: str): (optionnel) fonction de log globale
        """
        super().__init__(parent)
        self.app_ctx = app_ctx
        self.proc = None

        root = QVBoxLayout(self)

        # --- Ligne boutons d'action ---
        actions = QGroupBox("Actions")
        a_layout = QHBoxLayout(actions)

        self.btn_update_app = QPushButton("Mettre à jour l’app")
        self.btn_restart    = QPushButton("Redémarrer")
        self.btn_update_txt = QPushButton("Mettre à jour le txt")

        a_layout.addWidget(self.btn_update_app)
        a_layout.addWidget(self.btn_restart)
        a_layout.addWidget(self.btn_update_txt)

        # --- Switch thème dans Paramètres ---
        theme_box = QGroupBox("Apparence")
        t_layout = QHBoxLayout(theme_box)
        self.chk_dark = QCheckBox("Mode sombre")
        self.lbl_theme = QLabel("")  # affichera "Mode sombre" / "Mode clair"
        self.chk_dark.setChecked(self.app_ctx.current_theme() == "dark")
        self._update_theme_label()
        t_layout.addWidget(self.chk_dark)
        t_layout.addWidget(self.lbl_theme)
        t_layout.addStretch(1)

        # --- Console ---
        console_box = QGroupBox("Console")
        c_layout = QVBoxLayout(console_box)
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        c_layout.addWidget(self.console)

        # Assemblage
        root.addWidget(actions)
        root.addWidget(theme_box)
        root.addWidget(console_box)
        root.addStretch(1)

        # Signals
        self.btn_update_app.clicked.connect(self._on_update_app)
        self.btn_restart.clicked.connect(self._on_restart)
        self.btn_update_txt.clicked.disconnect() if hasattr(self.btn_update_txt, "clicked") else None
        self.btn_update_txt.clicked.connect(self._on_update_copy_txt)
        self.chk_dark.stateChanged.connect(self._on_theme_toggled)

    # ==== Actions ====
    def _append(self, text: str):
        self.console.appendPlainText(text)

    def _run_process(self, program: str, args: list[str], cwd: Path):
        # Lance un QProcess et pipe stdout/stderr vers la console
        if self.proc:
            self.proc.kill()
            self.proc = None
        self.proc = QProcess(self)
        self.proc.setProgram(program)
        self.proc.setArguments(args)
        self.proc.setWorkingDirectory(str(cwd))
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(
            lambda: self._append(bytes(self.proc.readAllStandardOutput()).decode(errors="replace"))
        )
        self.proc.readyReadStandardError.connect(
            lambda: self._append(bytes(self.proc.readAllStandardError()).decode(errors="replace"))
        )
        self.proc.started.connect(lambda: self._append(f"> {program} {' '.join(args)} (cwd={cwd})"))
        self.proc.finished.connect(lambda code, _status: self._append(f"[exit {code}]"))
        self.proc.start()

    def _on_update_app(self):
        # git pull origin main dans la racine du projet
        root = self.app_ctx.root_dir
        git = "git.exe" if os.name == "nt" else "git"
        self._run_process(git, ["pull", "origin", "main"], root)

    def _on_restart(self):
        self._append("Redémarrage en cours…")
        # Flush puis relance le process
        self._restart_app()

    def _on_update_copy_txt(self):
        # racine du projet
        root = detect_project_root(Path(__file__).resolve())
        out_path = root / "copy.txt"
        stats = build_copy_txt(root, out_path)
        # log UI
        try:
            self.console.appendPlainText(
                f"copy.txt mis à jour: {stats['files']} fichiers, {stats['bytes']} octets → {stats['out']}"
            )
        except Exception:
            pass
        toast(self, "copy.txt mis à jour", "success")

    # ==== Thème ====
    def _update_theme_label(self):
        self.lbl_theme.setText("Mode sombre" if self.chk_dark.isChecked() else "Mode clair")

    def _on_theme_toggled(self, state):
        theme = "dark" if self.chk_dark.isChecked() else "light"
        self.app_ctx.apply_theme(theme)
        self._update_theme_label()
        self._append(f"Thème appliqué: {theme}")

    # ==== Restart ====
    def _restart_app(self):
        # relance le processus Python courant avec les mêmes arguments
        python = sys.executable
        os.execl(python, python, *sys.argv)
