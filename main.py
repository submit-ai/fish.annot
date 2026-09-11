import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow

APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #F5F7FA;
    font-family: "Segoe UI";
    font-size: 10pt;
    color: #1F2933;
}

/* Header */
QWidget#app_header { background-color: #1A365D; }
QLabel#header_title {
    color: #FFFFFF; font-size: 14pt; font-weight: bold;
    background-color: transparent;
}
QLabel#header_version {
    color: #90CDF4; font-size: 10pt;
    background-color: transparent; padding-top: 4px;
}
QLabel#header_subtitle {
    color: #90CDF4; font-size: 9pt;
    background-color: transparent; padding-top: 2px;
}

/* GroupBox as card */
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #D9E2EC;
    border-radius: 4px;
    margin-top: 10px;
    font-size: 8pt;
    font-weight: bold;
    color: #52606D;
    padding: 6px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #52606D;
    background-color: #FFFFFF;
}

/* Inputs */
QLineEdit, QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #D9E2EC;
    border-radius: 3px;
    padding: 4px 8px;
    color: #1F2933;
}
QLineEdit:focus, QSpinBox:focus { border-color: #2B6CB0; }
QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #D9E2EC;
    border-radius: 3px;
    padding: 4px 8px;
    color: #1F2933;
}
QComboBox:focus { border-color: #2B6CB0; }
QComboBox::drop-down { border: none; padding-right: 6px; }

/* Info tab buttons */
QPushButton#tab_btn {
    background-color: #CBD5E0;
    color: #1F2933;
    border-radius: 3px;
    padding: 3px 10px;
    font-size: 9pt;
    font-weight: bold;
}
QPushButton#tab_btn:checked {
    background-color: #2B5282;
    color: #FFFFFF;
}
QPushButton#tab_btn:hover:!checked { background-color: #A0AEC0; }

/* Annotation form — compact inputs */
QGroupBox#form_group QLineEdit,
QGroupBox#form_group QSpinBox,
QGroupBox#form_group QComboBox {
    padding: 2px 6px;
    font-size: 9pt;
}
QGroupBox#form_group QPushButton,
QGroupBox#form_group QCheckBox,
QGroupBox#form_group QLabel {
    font-size: 9pt;
}

/* Buttons — default neutral */
QPushButton {
    background-color: #4A5568;
    color: #FFFFFF;
    border: none;
    border-radius: 3px;
    padding: 6px 14px;
    font-weight: bold;
}
QPushButton:hover { background-color: #374151; }
QPushButton:disabled { background-color: #A0AEC0; color: #EDF2F7; }

QPushButton#btn_primary             { background-color: #276749; }
QPushButton#btn_primary:hover       { background-color: #1A4731; }
QPushButton#btn_primary:disabled    { background-color: #A0AEC0; }

QPushButton#btn_secondary           { background-color: #2B5282; }
QPushButton#btn_secondary:hover     { background-color: #1E3A5F; }
QPushButton#btn_secondary:disabled  { background-color: #A0AEC0; }

QPushButton#btn_danger              { background-color: #9B2335; }
QPushButton#btn_danger:hover        { background-color: #7B1C2A; }
QPushButton#btn_danger:disabled     { background-color: #A0AEC0; }

/* Table */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #D9E2EC;
    gridline-color: #EDF2F7;
    alternate-background-color: #F7FAFC;
}
QTableWidget::item { padding: 4px; color: #1F2933; }
QTableWidget::item:selected { background-color: #EBF8FF; color: #1F2933; }
QHeaderView::section {
    background-color: #F5F7FA;
    color: #52606D;
    font-weight: bold;
    font-size: 9pt;
    border: none;
    border-right: 1px solid #D9E2EC;
    border-bottom: 1px solid #D9E2EC;
    padding: 5px 8px;
}

/* MenuBar */
QMenuBar {
    background-color: #FFFFFF;
    color: #1F2933;
    border-bottom: 1px solid #D9E2EC;
}
QMenuBar::item { padding: 4px 10px; background-color: transparent; }
QMenuBar::item:selected { background-color: #EBF8FF; }
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #D9E2EC;
    color: #1F2933;
}
QMenu::item { padding: 5px 20px; }
QMenu::item:selected { background-color: #EBF8FF; }

/* StatusBar */
QStatusBar {
    background-color: #FFFFFF;
    border-top: 1px solid #D9E2EC;
    color: #52606D;
    font-size: 9pt;
    padding: 2px 8px;
}

/* Help button in header */
QPushButton#btn_help {
    background-color: transparent;
    color: #90CDF4;
    border: 1px solid #90CDF4;
    border-radius: 12px;
    font-size: 12pt;
    font-weight: bold;
    padding: 0;
}
QPushButton#btn_help:hover {
    background-color: #2B5282;
    color: #FFFFFF;
    border-color: #FFFFFF;
}

/* ScrollBar */
QScrollBar:vertical {
    background-color: #F5F7FA; width: 10px; border: none;
}
QScrollBar::handle:vertical {
    background-color: #CBD5E0; border-radius: 5px; min-height: 20px;
}
QScrollBar::handle:vertical:hover { background-color: #A0AEC0; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background-color: #F5F7FA; height: 10px; border: none;
}
QScrollBar::handle:horizontal {
    background-color: #CBD5E0; border-radius: 5px; min-width: 20px;
}
QScrollBar::handle:horizontal:hover { background-color: #A0AEC0; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* Image viewer */
QGraphicsView {
    background-color: #2D3748;
    border: 1px solid #D9E2EC;
}

/* CheckBox */
QCheckBox { color: #1F2933; spacing: 6px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #D9E2EC;
    border-radius: 2px;
    background-color: #FFFFFF;
}
QCheckBox::indicator:checked {
    background-color: #2B6CB0;
    border-color: #2B6CB0;
}
"""


def _resource(rel):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    icon_path = _resource(os.path.join("assets", "icon.ico"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
