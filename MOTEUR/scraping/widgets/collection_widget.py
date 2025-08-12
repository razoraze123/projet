from __future__ import annotations

from PySide6.QtCore import QObject, Signal, QThread, Slot, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)


class _CollectionWorker(QObject):
    result = Signal(list)
    error = Signal(str)
    progress = Signal(str)
    cancelled = Signal()

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url
        self._cancelled = False
        self._driver = None  # type: ignore

    def cancel(self) -> None:
        self._cancelled = True
        try:
            if self._driver:
                self._driver.quit()
        except Exception:
            pass

    @Slot()
    def run(self) -> None:
        try:
            self.progress.emit("⏳ Ouverture de la page…")
            from MOTEUR.scraping.image_scraper import (
                scrape_collection_products_cancelable,
            )

            pairs = scrape_collection_products_cancelable(
                self._url,
                self._set_driver,
                self._is_cancelled,
                self.progress.emit,
            )
            if self._cancelled:
                self.cancelled.emit()
                return
            self.result.emit(pairs)
        except Exception as e:
            if self._cancelled:
                self.cancelled.emit()
            else:
                self.error.emit(str(e))

    def _set_driver(self, drv) -> None:
        self._driver = drv

    def _is_cancelled(self) -> bool:
        return self._cancelled


class CollectionWidget(QWidget):
    """UI widget to list products from a collection page."""

    def __init__(self) -> None:
        super().__init__()
        self._pairs: list[tuple[str, str]] = []

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("URL de la page collection")

        self.list_btn = QPushButton("Scanner la collection")
        self.list_btn.clicked.connect(self._scan_collection)

        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)

        self.save_btn = QPushButton("Enregistrer la liste…")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_list)

        self.console = QTextEdit(readOnly=True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("URL :"))
        layout.addWidget(self.url_edit)

        row = QHBoxLayout()
        row.addWidget(self.list_btn)
        row.addWidget(self.cancel_btn)
        row.addWidget(self.save_btn)
        layout.addLayout(row)
        layout.addWidget(self.console)

        self._thread: QThread | None = None
        self._worker: _CollectionWorker | None = None

    # ------------------------------------------------------------------
    def _set_busy(self, busy: bool) -> None:
        self.list_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.save_btn.setEnabled((not busy) and bool(self._pairs))
        if busy:
            QGuiApplication.setOverrideCursor(Qt.BusyCursor)
        else:
            QGuiApplication.restoreOverrideCursor()

    # ------------------------------------------------------------------
    @Slot()
    def _scan_collection(self) -> None:
        url = (self.url_edit.text() or "").strip()
        if not url:
            self.console.append("❌ Saisis une URL de collection.")
            return
        if self._thread and self._thread.isRunning():
            return
        self.console.append("▶️ Scan démarré…")
        self._set_busy(True)

        self._thread = QThread(self)
        self._worker = _CollectionWorker(url)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.console.append)
        self._worker.result.connect(self._on_scan_ok)
        self._worker.error.connect(self._on_scan_err)
        self._worker.cancelled.connect(self._on_scan_cancelled)

        for sig in (
            self._worker.result,
            self._worker.error,
            self._worker.cancelled,
        ):
            sig.connect(self._thread.quit)
        self._thread.finished.connect(lambda: self._set_busy(False))
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    @Slot()
    def _save_list(self) -> None:
        if not self._pairs:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer la liste",
            "",
            "Text files (*.txt)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                for name, href in self._pairs:
                    f.write(f"{name}\t{href}\n")
        except Exception as exc:
            QMessageBox.critical(self, "Export", f"Erreur: {exc}")
            return
        QMessageBox.information(self, "Export", f"✅ Liste enregistrée : {path}")

    # ------------------------------------------------------------------
    @Slot()
    def _on_cancel_clicked(self) -> None:
        if self._worker:
            self.cancel_btn.setEnabled(False)
            self.console.append("🛑 Annulation demandée…")
            self._worker.cancel()

    @Slot(list)
    def _on_scan_ok(self, pairs: list) -> None:
        self._pairs = pairs or []
        if not pairs:
            self.console.append("⚠️ Aucun produit détecté.")
            self.save_btn.setEnabled(False)
        else:
            self.console.append(f"✅ {len(pairs)} produits trouvés.")
            self.save_btn.setEnabled(True)

    @Slot(str)
    def _on_scan_err(self, message: str) -> None:
        self.console.append(f"❌ Erreur collecte: {message}")

    @Slot()
    def _on_scan_cancelled(self) -> None:
        self.console.append("🟡 Scan annulé.")
