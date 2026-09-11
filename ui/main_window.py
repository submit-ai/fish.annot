from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QDialog, QTextEdit
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
import os
import sys

from ui.annotation_tab import AnnotationTab
from ui.prepare_tab import PrepareTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FISH ANNOT v2")
        self.resize(1800, 1000)

        self.annotation_tab = AnnotationTab()
        self.prepare_tab = PrepareTab()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.annotation_tab, "Annotate")
        self.tabs.addTab(self.prepare_tab, "Prepare")

        header = self._build_header()

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(header)
        outer.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        self.annotation_tab.status_message.connect(self._on_status_message)
        self.annotation_tab.title_changed.connect(self.setWindowTitle)

        self.statusBar().showMessage("Ready")

    def closeEvent(self, event):
        # A build runs in a QThread owned by the Prepare tab; letting the window go
        # while it is still running makes Qt abort the process.
        self.prepare_tab.shutdown()
        super().closeEvent(event)

    def _build_header(self):
        header = QWidget()
        header.setObjectName("app_header")
        header.setFixedHeight(38)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 0, 22, 0)
        layout.setSpacing(6)

        lbl_title = QLabel("FISH ANNOT")
        lbl_title.setObjectName("header_title")
        lbl_ver = QLabel("v2")
        lbl_ver.setObjectName("header_version")
        lbl_sub = QLabel("  Manual annotation tool")
        lbl_sub.setObjectName("header_subtitle")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_ver)
        layout.addWidget(lbl_sub)
        layout.addStretch()

        help_btn = QPushButton("?")
        help_btn.setObjectName("btn_help")
        help_btn.setFixedSize(24, 24)
        help_btn.setToolTip("User guide")
        help_btn.clicked.connect(self._show_help)
        layout.addWidget(help_btn)

        return header

    def _on_status_message(self, msg, timeout):
        self.statusBar().showMessage(msg, timeout)

    def _show_help(self):
        from ui.help_content import HELP_HTML
        dlg = QDialog(self)
        dlg.setWindowTitle("FISH Annot — User Guide")
        dlg.resize(720, 600)
        dlg.setMinimumSize(520, 420)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet(
            "QTextEdit { background:#FFFFFF; border:none; padding:20px;"
            " font-family:'Segoe UI'; font-size:10pt; color:#1F2933; }"
        )
        txt.setHtml(HELP_HTML)
        layout.addWidget(txt)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(16, 8, 16, 16)
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("btn_secondary")
        close_btn.setFixedHeight(30)
        close_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        dlg.exec()
