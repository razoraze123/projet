from __future__ import annotations

from PySide6.QtCore import QObject, Signal, QThread, Slot, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QDesktopServices
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
    QGroupBox,
    QRadioButton,
    QSpinBox,
    QPlainTextEdit,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
)
import csv

from ...common.fileio import write_lines_txt
from .. import history
from ui_helpers import show_toast


VERSION_COLLECTION_WIDGET = 3  # pagination modes + live logs


class _CollectionWorker(QObject):
    result = Signal(list)
    error = Signal(str)
    progress = Signal(str)
    page_progress = Signal(str)
    link_found = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        mode: str,
        base_url: str,
        template: str | None,
        start: int,
        end: int,
        urls_list: list[str] | None,
        live_logs: bool,
        max_pages: int = 20,
    ) -> None:
        super().__init__()
        self._mode = mode
        self._base_url = base_url
        self._template = template
        self._start = start
        self._end = end
        self._urls_list = urls_list or []
        self._live_logs = live_logs
        self._max_pages = max_pages
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
            from MOTEUR.scraping.image_scraper import (
                generate_page_urls,
                scrape_collection_products_paginated,
            )

            if self._mode == "auto":
                pages = [self._base_url]
                auto = True
            elif self._mode == "range":
                pages = generate_page_urls(self._template or "", self._start, self._end)
                auto = False
            else:
                pages = [u.strip() for u in self._urls_list if u.strip()]
                auto = False

            link_cb = self.link_found.emit if self._live_logs else None

            def page_cb(idx: int, total: int, new: int, total_links: int) -> None:
                self.page_progress.emit(
                    f"Page {idx}/{total} — +{new} liens, total {total_links}"
                )

            urls = scrape_collection_products_paginated(
                pages,
                self._set_driver,
                self._is_cancelled,
                self.progress.emit,
                link_cb,
                page_cb,
                auto_follow=auto,
                max_pages=self._max_pages,
            )
            if self._cancelled:
                self.cancelled.emit()
                return
            self.result.emit(urls)
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
        self._urls: list[str] = []

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("URL de la page collection")

        # Pagination modes -------------------------------------------------
        self.pagination_group = QGroupBox("Pagination")
        self.mode_auto = QRadioButton("Auto (lien Suivant)")
        self.mode_range = QRadioButton("Plage {page}")
        self.mode_list = QRadioButton("Liste d'URLs")
        self.mode_auto.setChecked(True)
        pg_layout = QVBoxLayout(self.pagination_group)
        pg_layout.addWidget(self.mode_auto)
        pg_layout.addWidget(self.mode_range)
        pg_layout.addWidget(self.mode_list)
        self.mode_auto.toggled.connect(self._update_modes)
        self.mode_range.toggled.connect(self._on_range_mode)
        self.mode_list.toggled.connect(self._update_modes)

        # Range widgets ----------------------------------------------------
        self.range_widget = QWidget()
        rw_layout = QHBoxLayout(self.range_widget)
        self.template_edit = QLineEdit()
        self.template_edit.setPlaceholderText(
            "ex. ...?page={page} ou /page/{page}"
        )
        self.start_spin = QSpinBox()
        self.start_spin.setMinimum(1)
        self.start_spin.setValue(1)
        self.end_spin = QSpinBox()
        self.end_spin.setMinimum(1)
        self.end_spin.setValue(6)
        self.preview_btn = QPushButton("Prévisualiser")
        self.preview_btn.clicked.connect(self._preview_range)
        rw_layout.addWidget(self.template_edit)
        rw_layout.addWidget(self.start_spin)
        rw_layout.addWidget(self.end_spin)
        rw_layout.addWidget(self.preview_btn)

        # List widgets -----------------------------------------------------
        self.list_widget = QWidget()
        lw_layout = QVBoxLayout(self.list_widget)
        self.urls_edit = QPlainTextEdit()
        lw_layout.addWidget(self.urls_edit)

        # Options ----------------------------------------------------------
        self.live_logs_cb = QCheckBox("Afficher les liens en direct")
        self.live_logs_cb.setChecked(True)
        self.show_live_cb = self.live_logs_cb

        self.stats_lbl = getattr(self, "stats_lbl", None) or QLabel(
            "Liens détectés : 0", self
        )
        self.badge_busy = getattr(self, "badge_busy", None) or QLabel("", self)
        self.badge_busy.setVisible(False)
        self.badge_busy.setStyleSheet(
            "QLabel{padding:3px 8px; border-radius:9px; background:#9E9E9E; color:white; font-weight:600;}"
        )

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
        layout.addWidget(self.pagination_group)
        layout.addWidget(self.range_widget)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.live_logs_cb)
        layout.addWidget(self.stats_lbl)

        row = QHBoxLayout()
        row.addWidget(self.list_btn)
        row.addWidget(self.cancel_btn)
        row.addWidget(self.save_btn)
        row.addWidget(self.badge_busy)
        layout.addLayout(row)

        layout.addWidget(self.console)

        self.live_list = getattr(self, "live_list", None) or QListWidget(self)
        self.live_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.live_list.itemActivated.connect(
            lambda item: QDesktopServices.openUrl(QUrl(item.text()))
        )
        layout.addWidget(self.live_list)

        actions = QHBoxLayout()
        self.copy_btn = QPushButton("Tout copier")
        self.copy_btn.clicked.connect(self._copy_links)
        self.dedupe_btn = QPushButton("🧹 Supprimer doublons")
        self.dedupe_btn.clicked.connect(self._dedupe_urls)
        self.export_csv_btn = QPushButton("Exporter CSV")
        self.export_csv_btn.clicked.connect(self._export_csv)
        self.clear_btn = QPushButton("Effacer la console")
        self.clear_btn.clicked.connect(self.console_clear)
        actions.addWidget(self.copy_btn)
        actions.addWidget(self.dedupe_btn)
        actions.addWidget(self.export_csv_btn)
        actions.addWidget(self.clear_btn)
        layout.addLayout(actions)

        self.range_widget.hide()
        self.list_widget.hide()

        self._thread: QThread | None = None
        self._worker: _CollectionWorker | None = None

    # ------------------------------------------------------------------
    def showEvent(self, event):  # type: ignore[override]
        super().showEvent(event)
        try:
            data = history.load_last_used()
            if data and not self.url_edit.text().strip():
                self.url_edit.setText(data.get("url", ""))
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _set_busy(self, busy: bool) -> None:
        self.list_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.save_btn.setEnabled((not busy) and bool(self._urls))
        self.badge_busy.setText("EN COURS…" if busy else "")
        self.badge_busy.setVisible(busy)
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

        mode = "auto"
        template = None
        start = self.start_spin.value()
        end = self.end_spin.value()
        urls_list = None
        if self.mode_range.isChecked():
            mode = "range"
            template = (self.template_edit.text() or "").strip()
        elif self.mode_list.isChecked():
            mode = "list"
            urls_list = [u.strip() for u in self.urls_edit.toPlainText().splitlines() if u.strip()]

        self.console.append("▶️ Scan démarré…")
        self._urls = []
        self.stats_lbl.setText("Liens détectés : 0")
        self.live_list.clear()
        self._set_busy(True)

        self._thread = QThread(self)
        self._worker = _CollectionWorker(
            mode,
            url,
            template,
            start,
            end,
            urls_list,
            self.live_logs_cb.isChecked(),
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.console.append)
        self._worker.page_progress.connect(self.stats_lbl.setText)
        self._worker.link_found.connect(self._on_link_detected)
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
        if not self._urls:
            QMessageBox.information(self, "Enregistrer", "Aucune donnée.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer la liste",
            "liens bob.txt",  # nom proposé
            "Text files (*.txt)"
        )
        if not path:
            return
        if not path.lower().endswith(".txt"):
            path += ".txt"

        urls = self._urls

        try:
            saved_path = write_lines_txt(path, urls)
            QMessageBox.information(
                self, "Enregistrer", f"✅ Liens enregistrés : {saved_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Enregistrer", f"Erreur: {e}")

    # ------------------------------------------------------------------
    @Slot()
    def _on_cancel_clicked(self) -> None:
        if self._worker:
            self.cancel_btn.setEnabled(False)
            self.console.append("🛑 Annulation demandée…")
            self._worker.cancel()

    @Slot(list)
    def _on_scan_ok(self, urls: list) -> None:
        self._urls = urls or []
        self.stats_lbl.setText(f"Liens détectés : {len(self._urls)}")
        if not urls:
            self.console.append("⚠️ Aucun produit détecté.")
            self.save_btn.setEnabled(False)
        else:
            self.console.append(f"✅ {len(urls)} liens trouvés.")
            self.save_btn.setEnabled(True)
        try:
            data = history.load_last_used()
            history.save_last_used(self.url_edit.text().strip(), data.get("folder", ""))
        except Exception:
            pass

    @Slot(str)
    def _on_scan_err(self, message: str) -> None:
        self.console.append(f"❌ Erreur collecte: {message}")

    @Slot()
    def _on_scan_cancelled(self) -> None:
        self.console.append("🟡 Scan annulé.")

    # ------------------------------------------------------------------
    def _update_modes(self) -> None:
        self.range_widget.setVisible(self.mode_range.isChecked())
        self.list_widget.setVisible(self.mode_list.isChecked())

    def _on_range_mode(self, checked: bool) -> None:
        self._update_modes()
        if checked:
            from MOTEUR.scraping.image_scraper import infer_pagination_template

            tpl, start = infer_pagination_template(self.url_edit.text().strip())
            if tpl:
                self.template_edit.setText(tpl)
                self.start_spin.setValue(start)

    def _preview_range(self) -> None:
        from MOTEUR.scraping.image_scraper import generate_page_urls

        tpl = (self.template_edit.text() or "").strip()
        if not tpl:
            self.console.append("⚠️ Fournis un template valide.")
            return
        urls = generate_page_urls(tpl, self.start_spin.value(), self.end_spin.value())
        for u in urls:
            self.console.append(u)

    def _copy_links(self) -> None:
        if not self._urls:
            return
        QGuiApplication.clipboard().setText("\n".join(self._urls))
        show_toast(self, "Liens copiés dans le presse-papiers.")

    def console_clear(self) -> None:
        self.console.clear()

    # ------------------------------------------------------------------
    def _on_link_detected(self, url: str) -> None:
        self._urls.append(url)
        self.stats_lbl.setText(f"Liens détectés : {len(self._urls)}")
        self.console.append(url)
        if self.show_live_cb.isChecked():
            item = QListWidgetItem(url)
            item.setToolTip(url)
            self.live_list.addItem(item)

    def _dedupe_urls(self) -> None:
        before = len(self._urls)
        self._urls = list(dict.fromkeys(self._urls))
        after = len(self._urls)
        self.stats_lbl.setText(f"Liens détectés : {after} (−{before-after} doublons)")
        if self.show_live_cb.isChecked():
            self.live_list.clear()
            for u in self._urls:
                item = QListWidgetItem(u)
                item.setToolTip(u)
                self.live_list.addItem(item)

    def _export_csv(self) -> None:
        if not self._urls:
            QMessageBox.information(self, "Exporter", "Aucune donnée.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter CSV",
            "liens.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["url"])
                for u in self._urls:
                    writer.writerow([u])
            QMessageBox.information(
                self, "Exporter", f"✅ Liens exportés : {path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Exporter", f"Erreur: {e}")
