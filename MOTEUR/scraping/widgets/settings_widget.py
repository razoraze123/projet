from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QTextEdit,
)
from PySide6.QtCore import Signal, Slot, QCoreApplication, QProcess
from pathlib import Path
import os

try:
    from localapp.log_safe import open_utf8
except ImportError:
    from log_safe import open_utf8


class ScrapingSettingsWidget(QWidget):
    module_toggled = Signal(str, bool)
    rename_toggled = Signal(bool)

    def __init__(self, modules_order=None, *, show_maintenance: bool = False):
        super().__init__()
        from ..utils.restart import relaunch_current_process
        from ..utils.update import PROJECT_ROOT

        layout = QVBoxLayout(self)
        # (conserver vos éléments existants ici)
        _ = (modules_order or [])

        self._project_root = PROJECT_ROOT
        self._relaunch_current_process = relaunch_current_process

        if show_maintenance:
            self._build_maintenance_ui(layout)

    # ------------------------------------------------------------------
    def _build_maintenance_ui(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        self.update_btn = QPushButton("Mettre à jour")
        self.update_btn.setObjectName("btn_update")
        self.restart_btn = QPushButton("Redémarrer")
        self.restart_btn.setObjectName("btn_restart")
        row.addWidget(self.update_btn)
        row.addWidget(self.restart_btn)
        self.copy_btn = QPushButton("Mettre à jour le txt")
        row.addWidget(self.copy_btn)
        layout.addLayout(row)

        # Simple log output
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)

        # Prepare git QProcess
        self._git_proc = QProcess(self)
        self._git_proc.readyReadStandardOutput.connect(
            lambda: self._append_log(
                bytes(self._git_proc.readAllStandardOutput()).decode("utf-8", "ignore")
            )
        )
        self._git_proc.readyReadStandardError.connect(
            lambda: self._append_log(
                bytes(self._git_proc.readAllStandardError()).decode("utf-8", "ignore")
            )
        )
        self._git_proc.finished.connect(self._on_git_finished)

        self.update_btn.clicked.connect(self._on_update_clicked)
        self.restart_btn.clicked.connect(self._on_restart_clicked)
        self.copy_btn.clicked.connect(self._on_generate_copy_clicked)

    # ------------------------------------------------------------------
    def _append_log(self, text: str) -> None:
        if hasattr(self, "log_edit") and self.log_edit is not None:
            txt = text.strip()
            if txt:
                self.log_edit.append(txt)

    # ------------------------------------------------------------------
    @Slot()
    def _on_update_clicked(self) -> None:
        root = Path(self._project_root)
        if not (root / ".git").exists():
            QMessageBox.critical(
                self, "Mettre à jour", f"Aucun dépôt Git détecté dans :\n{root}"
            )
            return

        self.update_btn.setEnabled(False)
        self.update_btn.setText("Mise à jour en cours…")
        self._append_log(f"> git pull origin main (cwd={root})")
        self._git_proc.setWorkingDirectory(str(root))
        self._git_proc.start("git", ["pull", "origin", "main"])

        if not self._git_proc.waitForStarted(2000):
            self.update_btn.setEnabled(True)
            self.update_btn.setText("Mettre à jour")
            QMessageBox.critical(
                self,
                "Mettre à jour",
                "Impossible de démarrer Git. Est-il installé et dans le PATH ?",
            )

    # ------------------------------------------------------------------
    def _on_git_finished(self, code: int, status) -> None:
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Mettre à jour")
        if code == 0:
            QMessageBox.information(self, "Mettre à jour", "Mise à jour réussie.")
        else:
            QMessageBox.critical(
                self,
                "Mettre à jour",
                f"Échec du 'git pull' (code {code}). Consulte les logs.",
            )

    # ------------------------------------------------------------------
    @Slot()
    def _on_restart_clicked(self) -> None:
        ret = QMessageBox.question(
            self,
            "Redémarrer",
            "Voulez-vous vraiment redémarrer l’application ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        self._relaunch_current_process(delay_sec=0.3)
        QCoreApplication.quit()

    # ------------------------------------------------------------------
    @Slot()
    def _on_generate_copy_clicked(self) -> None:
        root = Path(self._project_root)  # défini dans __init__
        out = root / "copy.txt"
        ignore_dirs = {".git", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache", "images"}
        max_size = 800_000  # ignore fichiers texte > 800 KB

        try:
            with open_utf8(out, "w") as w:   # <= ÉCRASE à chaque clic
                for dirpath, dirnames, filenames in os.walk(root):
                    dn = os.path.basename(dirpath)
                    if dn in ignore_dirs:
                        continue
                    for fn in sorted(filenames):
                        p = Path(dirpath) / fn
                        if not _is_textlike(p):
                            continue
                        try:
                            if p.stat().st_size > max_size:
                                # trop gros, on documente et skip
                                rel = p.relative_to(root).as_posix()
                                w.write(f"\n\n# {rel}\n")
                                w.write(f"Description: [skipped: file too large]\n\n")
                                continue
                            content = p.read_text(encoding="utf-8")
                        except Exception:
                            rel = p.relative_to(root).as_posix()
                            w.write(f"\n\n# {rel}\n")
                            w.write("Description: [skipped: non-text or undecodable]\n\n")
                            continue

                        rel = p.relative_to(root).as_posix()
                        w.write(f"\n\n# {rel}\n")
                        w.write(f"Description: Source code for {rel}\n")
                        w.write("```\n")
                        w.write(content)
                        w.write("\n```\n")
            self._append_log(f"✅ copy.txt régénéré : {out}")
        except Exception as e:
            self._append_log(f"❌ Erreur génération copy.txt : {e}")


def _is_textlike(p: Path) -> bool:
    # Ajuste ici si besoin d’autres extensions
    exts = {".py", ".txt", ".md", ".json", ".yml", ".yaml", ".ini", ".cfg", ".toml", ".csv"}
    return p.suffix.lower() in exts


