from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QLineEdit,
    QFileDialog,
    QHBoxLayout,
    QComboBox,
    QCheckBox,
    QApplication,
    QMessageBox,
)
from PySide6.QtCore import Qt, Slot, QThread, QTimer, QProcess, QProcessEnvironment
from PySide6.QtGui import QClipboard
from pathlib import Path

try:
    from localapp.log_safe import open_utf8
except ImportError:
    from log_safe import open_utf8
from .. import profile_manager as pm
from .. import history


class ImageScraperWidget(QWidget):
    """Simple interface to run the image scraper."""

    def __init__(self, *, storage_widget=None) -> None:
        super().__init__()

        self.storage_widget = storage_widget

        self.export_data: list[dict[str, str]] = []

        self.file_edit = QLineEdit()
        # ✅ Alias de compatibilité pour l'ancien code
        self.url_edit = self.file_edit
        self.file_edit.setPlaceholderText("Fichier texte contenant les URLs")
        file_btn = QPushButton("Parcourir…")
        file_btn.clicked.connect(self._choose_file)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(file_btn)

        self.profile_combo = QComboBox()
        self.profiles: list[dict[str, str]] = []
        self.selected_selector: str = ""
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)

        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Dossier de destination")

        browse_btn = QPushButton("Parcourir…")
        browse_btn.clicked.connect(self._choose_folder)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(browse_btn)

        self.variants_checkbox = QCheckBox("Scraper aussi les variantes")
        self.isolate_checkbox = QCheckBox("Isoler (QProcess)")

        self.start_btn = QPushButton("Lancer")
        self.start_btn.clicked.connect(self._start)
        self.copy_btn = QPushButton("Copier")
        self.copy_btn.clicked.connect(self._copy_console)
        self.export_btn = QPushButton("Exporter")
        self.export_btn.clicked.connect(self._export_excel)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.copy_btn)
        buttons_layout.addWidget(self.export_btn)

        self.console = QTextEdit()
        self.console.setReadOnly(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        self._log_buffer: list[str] = []
        self._log_flusher = QTimer(self)
        self._log_flusher.setInterval(80)
        self._log_flusher.timeout.connect(self._flush_logs)
        self._log_flusher.start()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Fichier :"))
        layout.addLayout(file_layout)
        layout.addWidget(QLabel("Profil:"))
        layout.addWidget(self.profile_combo)
        layout.addWidget(QLabel("Dossier:"))
        layout.addLayout(folder_layout)
        layout.addWidget(self.variants_checkbox)
        layout.addWidget(self.isolate_checkbox)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.console)
        layout.addWidget(self.progress_bar)

        self.refresh_profiles()
        last = history.load_last_used()
        self.file_edit.setText(history.load_last_file() or "")
        self.folder_edit.setText(last.get("folder", ""))

    # ------------------------------------------------------------------
    def _on_profile_changed(self, index: int) -> None:
        if 0 <= index < len(self.profiles):
            self.selected_selector = self.profiles[index].get("selector", "")
        else:
            self.selected_selector = ""

    def set_selected_profile(self, profile: str) -> None:
        for i, p in enumerate(self.profiles):
            if p.get("name") == profile:
                self.profile_combo.setCurrentIndex(i)
                self.selected_selector = p.get("selector", "")
                return
        self.profile_combo.setCurrentIndex(-1)
        self.selected_selector = ""

    def refresh_profiles(self) -> None:
        self.profiles = pm.load_profiles()
        current = self.profile_combo.currentText()
        self.profile_combo.clear()
        for p in self.profiles:
            self.profile_combo.addItem(p.get("name", ""))
        # restore previous selection if possible
        if current:
            self.set_selected_profile(current)
        else:
            self._on_profile_changed(self.profile_combo.currentIndex())

    @Slot()
    def _choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if path:
            self.folder_edit.setText(path)

    @Slot()
    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un fichier",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            self.file_edit.setText(path)
            history.save_last_file(path)

    @Slot()
    def _copy_console(self) -> None:
        """Copy the console's contents to the clipboard."""
        text = self.console.toPlainText()
        QApplication.clipboard().setText(text, mode=QClipboard.Clipboard)
        # Also populate the selection clipboard on platforms that support it.
        QApplication.clipboard().setText(text, mode=QClipboard.Selection)

    @Slot()
    def _export_excel(self) -> None:
        """Export scraped variant data to an Excel file."""
        if not self.export_data:
            QMessageBox.information(self, "Export", "Aucune donnée à exporter.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer sous",
            "",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return

        try:
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            ws.append(["URL", "Variante", "Image"])
            for row in self.export_data:
                ws.append([row["URL"], row["Variant"], row["Image"]])
            wb.save(path)
        except Exception as exc:
            QMessageBox.critical(self, "Export", f"Erreur: {exc}")
            return

        QMessageBox.information(self, "Export", "Export termin\u00e9.")

    @Slot()
    def _start(self) -> None:
        file_path = self.file_edit.text().strip()
        selector = self.selected_selector.strip()
        folder = self.folder_edit.text().strip() or "images"
        if not file_path or not selector:
            self.console.append("❌ Fichier ou sélecteur manquant")
            return

        path = Path(file_path)
        if not path.is_file():
            self.console.append("❌ Fichier introuvable")
            return

        history.save_last_file(file_path)
        with open_utf8(path) as f:
            urls = [line.strip() for line in f if line.strip()]
        if not urls:
            self.console.append("❌ Aucun URL dans le fichier")
            return

        # UI prêt
        self.start_btn.setEnabled(False)
        self.console.clear()
        self.progress_bar.show()
        self.progress_bar.setRange(0, len(urls))
        self.progress_bar.setValue(0)
        self.export_data = []

        if self.isolate_checkbox.isChecked():
            args = [file_path, selector, folder, "1" if self.variants_checkbox.isChecked() else "0"]
            self._start_scrape_qprocess(args)
            return

        # thread + worker
        from .image_worker import ImageJobWorker
        self._thread = QThread(self)
        self._worker = ImageJobWorker(urls, selector, folder, self.variants_checkbox.isChecked())
        self._worker.moveToThread(self._thread)

        # connexions
        self._thread.started.connect(self._worker.run)
        self._worker.log.connect(lambda s: self._log_buffer.append(s))
        def _on_item_done(url, total, variants):
            self.console.append(f"✅ {url} - {total} images")
            for name, img in (variants or {}).items():
                self.console.append(f"  • {name}: {img}")
                self.export_data.append({"URL": url, "Variant": name, "Image": img})
            # Optionnel: push vers storage_widget
            if self.storage_widget and variants:
                self.storage_widget.add_product("", list(variants.keys()))
        self._worker.item_done.connect(_on_item_done)
        self._worker.progress.connect(self._on_progress)
        def _on_finished():
            self.progress_bar.hide()
            self.start_btn.setEnabled(True)
            self._thread.quit(); self._thread.wait()
            self._worker.deleteLater(); self._thread.deleteLater()
        self._worker.finished.connect(_on_finished)

        self._thread.start()

    def _start_scrape_qprocess(self, args: list[str]) -> None:
        import sys, json
        from pathlib import Path

        script = Path(__file__).resolve().parents[3] / "scrape_subprocess.py"
        self.proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUTF8", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        self.proc.setProcessEnvironment(env)
        self.proc.setProgram(sys.executable)
        self.proc.setArguments([str(script), *args])
        self.proc.readyReadStandardOutput.connect(self._on_proc_stdout)
        self.proc.finished.connect(self._on_proc_finished)
        self.proc.start()

    def _on_proc_stdout(self) -> None:
        import json

        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", errors="ignore")
        for line in data.splitlines():
            try:
                evt = json.loads(line)
            except Exception:
                self._log_buffer.append(line)
                continue
            if evt.get("event") == "log":
                self._log_buffer.append(evt.get("msg", ""))
            elif evt.get("event") == "progress":
                self._on_progress(int(evt.get("done", 0)), int(evt.get("total", 0)))
            elif evt.get("event") == "item":
                url = evt.get("url", "")
                total = evt.get("total", 0)
                self._log_buffer.append(f"✅ {url} - {total} images")
                variants = evt.get("variants") or {}
                for name, img in variants.items():
                    self._log_buffer.append(f"  • {name}: {img}")
                    self.export_data.append({"URL": url, "Variant": name, "Image": img})
                if self.storage_widget and variants:
                    self.storage_widget.add_product("", list(variants.keys()))
            elif evt.get("event") == "done":
                self._log_buffer.append(f"Terminé, total={evt.get('total', 0)}")

    def _on_proc_finished(self, code: int, status) -> None:
        self.progress_bar.hide()
        self.start_btn.setEnabled(True)
        self._log_buffer.append(f"Process scraping terminé (code={code}).")


    def _on_progress(self, done: int, total: int) -> None:
        self.progress_bar.setMaximum(max(1, total))
        self.progress_bar.setValue(done)
        if done == total or done % 3 == 0:
            self._log_buffer.append(f"Progression {done}/{total}")

    def _flush_logs(self) -> None:
        if not self._log_buffer:
            return
        chunk = "\n".join(self._log_buffer)
        self._log_buffer.clear()
        self.console.append(chunk)

