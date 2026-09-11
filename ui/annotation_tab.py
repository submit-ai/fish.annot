from pathlib import Path
from io import BytesIO
import datetime
import os
import json

from PIL import Image
Image.MAX_IMAGE_PIXELS = None

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QPen, QBrush, QPixmap, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core import app_paths
from core.metadata_loader import load_metadata, build_cell_index
from core.click_handler import compute_cell
from core import exporter
from core.exporter import save_csv_xlsx, draw_annotations, load_existing_annotations, export_crops_par_espece
from core.species_manager import load_species, save_species, SpeciesManagerDialog


class ImageGraphicsView(QGraphicsView):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event):
        if self.parent_window.pixmap_item is None:
            return

        factor = 1.05 ** (event.angleDelta().y() / 120)
        self.scale(factor, factor)
        self.parent_window.update_zoom_label()
        event.accept()

    def mousePressEvent(self, event):
        if self.parent_window.display_mode == "cell_hq" and self.parent_window.vertical_guide_item is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            guide_x = self.parent_window.vertical_guide_item.line().x1()

            if abs(scene_pos.x() - guide_x) < 12:
                self.parent_window.vertical_guide_dragging = True
                event.accept()
                return

        if event.button() == Qt.LeftButton and self.parent_window.pixmap_item is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.parent_window.handle_image_click_scene(scene_pos.x(), scene_pos.y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.parent_window.vertical_guide_dragging:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.parent_window.update_vertical_guide_from_scene_x(scene_pos.x())
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.parent_window.vertical_guide_dragging:
            self.parent_window.vertical_guide_dragging = False
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self.parent_window.pixmap_item is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.parent_window.handle_image_click_scene(scene_pos.x(), scene_pos.y())
            self.parent_window.zoom_on_cell_hq()
            self.parent_window.add_annotation()
        super().mouseDoubleClickEvent(event)

    def reset_zoom(self):
        self.resetTransform()
        self.parent_window.update_zoom_label()


class AnnotationTab(QWidget):
    status_message = Signal(str, int)   # message, timeout_ms (0 = permanent)
    title_changed = Signal(str)

    def __init__(self):
        super().__init__()

        self.folder = None
        self.meta = None
        self.cell_index = {}
        self.annotations = []
        self.species_list = load_species()
        self.drop_campaign = ""
        self.drop_location = ""
        self.drop_site = ""
        self.drop_id_value = ""
        self.drop_date = ""
        self.drop_latitude = ""
        self.drop_longitude = ""
        self.drop_habitat = ""
        self.drop_depth = ""
        self.drop_visibility = ""

        self.scene = QGraphicsScene()
        self.view = ImageGraphicsView(self)
        self.view.setScene(self.scene)

        self.pixmap_item = None
        self.preview_scale = 1.0
        self.selected_click_data = None
        self.selected_table_row = None
        self.right_panel_visible = True

        self.source_image_path = None
        self.source_image = None
        self.display_mode = "overview"
        self.current_hq_rect = None
        self.hq_scale = 1.0
        self.hq_display_cache = {}

        self.viewer_config_path = app_paths.config_file("viewer_config.json")
        self.vertical_guide_ratio = 0.5
        self.vertical_guide_item = None
        self.vertical_guide_dragging = False
        self._load_viewer_config()

        self._build_ui()
        self._build_menu()
        self._bind_keys()
        self.status_message.emit("Ready", 0)

    def _build_ui(self):
        self.zoom_input = QLineEdit("100%")
        self.zoom_input.setAlignment(Qt.AlignCenter)
        self.zoom_input.setMinimumWidth(48)
        self.zoom_input.editingFinished.connect(self._on_zoom_edit)

        self.v_input = QLineEdit("50.0%")
        self.v_input.setAlignment(Qt.AlignCenter)
        self.v_input.setMinimumWidth(44)
        self.v_input.editingFinished.connect(self._on_v_edit)

        def _stat_box(text, widget):
            frame = QFrame()
            frame.setMaximumHeight(28)
            frame.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            frame.setStyleSheet(
                "QFrame { background: #d4d4d4; border: 1px solid #aaa; border-radius: 3px; }"
            )
            row = QHBoxLayout(frame)
            row.setContentsMargins(5, 0, 5, 0)
            row.setSpacing(4)
            lbl = QLabel(text)
            lbl.setStyleSheet("background: transparent; border: none;")
            row.addWidget(lbl)
            widget.setStyleSheet(
                "QLineEdit { background: transparent; border: none; padding: 0; max-height: 22px; }"
                "QLineEdit:focus { background: #fff; border: 1px solid #4a90d9; border-radius: 2px; }"
            )
            row.addWidget(widget)
            return frame

        zoom_box = _stat_box("Zoom", self.zoom_input)
        v_box = _stat_box("V", self.v_input)

        self.reset_view_button = QPushButton("Overview")
        self.reset_view_button.setObjectName("btn_secondary")
        self.reset_view_button.clicked.connect(self.reset_to_overview)

        self.zoom_cell_button = QPushButton("HQ Cell Zoom")
        self.zoom_cell_button.setObjectName("btn_secondary")
        self.zoom_cell_button.clicked.connect(self.zoom_on_cell_hq)

        self.prev_in_col_button = QPushButton("↑ Previous image")
        self.prev_in_col_button.setObjectName("btn_secondary")
        self.prev_in_col_button.clicked.connect(self.go_prev_in_column)

        self.next_in_col_button = QPushButton("↓ Next image")
        self.next_in_col_button.setObjectName("btn_secondary")
        self.next_in_col_button.clicked.connect(self.go_next_in_column)

        self.toggle_panel_button = QPushButton("Hide panel")
        self.toggle_panel_button.setObjectName("btn_secondary")
        self.toggle_panel_button.clicked.connect(self.toggle_right_panel)

        self.fichier_button = QPushButton("File")

        for btn in (self.fichier_button, self.reset_view_button, self.zoom_cell_button,
                    self.prev_in_col_button, self.next_in_col_button,
                    self.toggle_panel_button):
            btn.setMaximumHeight(28)

        top_left = QHBoxLayout()
        top_left.setSpacing(4)
        top_left.setContentsMargins(0, 4, 0, 4)
        top_left.addWidget(self.fichier_button)
        top_left.addWidget(zoom_box)
        top_left.addWidget(v_box)
        top_left.addWidget(self.reset_view_button)
        top_left.addWidget(self.zoom_cell_button)
        top_left.addWidget(self.prev_in_col_button)
        top_left.addWidget(self.next_in_col_button)
        top_left.addWidget(self.toggle_panel_button)

        left_layout = QVBoxLayout()
        left_layout.addLayout(top_left)
        left_layout.addWidget(self.view)

        self.tab_btn_case = QPushButton("Selected cell")
        self.tab_btn_case.setObjectName("tab_btn")
        self.tab_btn_case.setCheckable(True)
        self.tab_btn_case.setChecked(True)
        self.tab_btn_case.setMaximumHeight(24)

        self.tab_btn_context = QPushButton("Metadata")
        self.tab_btn_context.setObjectName("tab_btn")
        self.tab_btn_context.setCheckable(True)
        self.tab_btn_context.setChecked(False)
        self.tab_btn_context.setMaximumHeight(24)

        tab_bar = QHBoxLayout()
        tab_bar.setSpacing(2)
        tab_bar.setContentsMargins(0, 0, 0, 0)
        tab_bar.addWidget(self.tab_btn_case)
        tab_bar.addWidget(self.tab_btn_context)
        tab_bar.addStretch()

        info_page = QWidget()
        info_layout = QFormLayout(info_page)
        info_layout.setSpacing(1)
        info_layout.setContentsMargins(4, 2, 4, 4)

        self.info_drop = QLabel("-")
        self.info_row = QLabel("-")
        self.info_col = QLabel("-")
        self.info_camera = QLabel("-")
        self.info_time_seconds = QLabel("-")
        self.info_time_label = QLabel("-")
        self.info_image_id = QLabel("-")
        self.info_image_file = QLabel("-")

        info_layout.addRow("Drop:", self.info_drop)
        info_layout.addRow("Row:", self.info_row)
        info_layout.addRow("Col:", self.info_col)
        info_layout.addRow("Camera:", self.info_camera)
        info_layout.addRow("Time (s):", self.info_time_seconds)
        info_layout.addRow("Time label:", self.info_time_label)
        info_layout.addRow("Image ID:", self.info_image_id)
        info_layout.addRow("Image file:", self.info_image_file)

        context_page = QWidget()
        context_layout = QGridLayout(context_page)
        context_layout.setSpacing(3)
        context_layout.setContentsMargins(4, 4, 4, 4)
        context_layout.setColumnStretch(1, 1)
        context_layout.setColumnStretch(3, 1)

        self.campaign_input = QLineEdit()
        self.location_input = QLineEdit()
        self.site_input = QLineEdit()
        self.drop_id_input = QLineEdit()
        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("YYYY-MM-DD")
        self.latitude_input = QLineEdit()
        self.longitude_input = QLineEdit()
        self.habitat_input = QLineEdit()
        self.habitat_input.setPlaceholderText("e.g. rocky, sandy…")
        self.depth_input = QLineEdit()
        self.depth_input.setPlaceholderText("e.g. 50m")
        self.visibility_input = QLineEdit()
        self.visibility_input.setPlaceholderText("e.g. good, 5m…")

        self.campaign_input.textChanged.connect(lambda v: setattr(self, "drop_campaign", v))
        self.location_input.textChanged.connect(lambda v: setattr(self, "drop_location", v))
        self.site_input.textChanged.connect(lambda v: setattr(self, "drop_site", v))
        self.drop_id_input.textChanged.connect(lambda v: setattr(self, "drop_id_value", v))
        self.date_input.textChanged.connect(lambda v: setattr(self, "drop_date", v))
        self.latitude_input.textChanged.connect(lambda v: setattr(self, "drop_latitude", v))
        self.longitude_input.textChanged.connect(lambda v: setattr(self, "drop_longitude", v))
        self.habitat_input.textChanged.connect(lambda v: setattr(self, "drop_habitat", v))
        self.depth_input.textChanged.connect(lambda v: setattr(self, "drop_depth", v))
        self.visibility_input.textChanged.connect(lambda v: setattr(self, "drop_visibility", v))

        def _lbl(text):
            l = QLabel(text)
            l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            return l

        context_layout.addWidget(_lbl("Campaign:"),  0, 0)
        context_layout.addWidget(self.campaign_input, 0, 1)
        context_layout.addWidget(_lbl("Location:"),  0, 2)
        context_layout.addWidget(self.location_input, 0, 3)

        context_layout.addWidget(_lbl("Site:"),      1, 0)
        context_layout.addWidget(self.site_input,    1, 1)
        context_layout.addWidget(_lbl("Drop ID:"),   1, 2)
        context_layout.addWidget(self.drop_id_input, 1, 3)

        context_layout.addWidget(_lbl("Date:"),      2, 0)
        context_layout.addWidget(self.date_input,    2, 1)
        context_layout.addWidget(_lbl("Latitude:"),  2, 2)
        context_layout.addWidget(self.latitude_input, 2, 3)

        context_layout.addWidget(_lbl("Longitude:"), 3, 0)
        context_layout.addWidget(self.longitude_input, 3, 1)
        context_layout.addWidget(_lbl("Habitat:"),   3, 2)
        context_layout.addWidget(self.habitat_input, 3, 3)

        context_layout.addWidget(_lbl("Depth:"),     4, 0)
        context_layout.addWidget(self.depth_input,   4, 1)
        context_layout.addWidget(_lbl("Visibility:"), 4, 2)
        context_layout.addWidget(self.visibility_input, 4, 3)

        self.update_context_button = QPushButton("Update metadata")
        self.update_context_button.setObjectName("btn_primary")
        self.update_context_button.setMaximumHeight(24)
        self.update_context_button.clicked.connect(self._update_context_all)
        context_layout.addWidget(self.update_context_button, 5, 0, 1, 4)

        self.info_stack = QStackedWidget()
        self.info_stack.addWidget(info_page)
        self.info_stack.addWidget(context_page)

        self.tab_btn_case.clicked.connect(lambda: self._switch_info_tab(0))
        self.tab_btn_context.clicked.connect(lambda: self._switch_info_tab(1))

        self.info_group = QGroupBox()
        info_group_layout = QVBoxLayout()
        info_group_layout.setSpacing(4)
        info_group_layout.setContentsMargins(6, 6, 6, 6)
        info_group_layout.addLayout(tab_bar)
        info_group_layout.addWidget(self.info_stack)
        self.info_group.setLayout(info_group_layout)

        self.form_group = QGroupBox("Annotation")
        self.form_group.setObjectName("form_group")
        form_layout = QFormLayout()
        form_layout.setSpacing(2)
        form_layout.setContentsMargins(4, 2, 4, 4)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Annotator name")

        self.species_combo = QComboBox()
        self._refresh_species_combo()

        self.manage_species_button = QPushButton("Manage species")
        self.manage_species_button.clicked.connect(self.manage_species)

        self.count_input = QSpinBox()
        self.count_input.setMinimum(1)
        self.count_input.setValue(1)

        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("Optional comment")

        self.uncertain_box = QCheckBox("Uncertain")

        self.add_button = QPushButton("Add")
        self.add_button.setObjectName("btn_primary")
        self.add_button.clicked.connect(self.add_annotation)

        self.update_button = QPushButton("Update")
        self.update_button.setObjectName("btn_secondary")
        self.update_button.clicked.connect(self.update_annotation)
        self.update_button.setEnabled(False)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("btn_danger")
        self.delete_button.clicked.connect(self.delete_selected_annotation)
        self.delete_button.setEnabled(False)

        self.undo_button = QPushButton("Undo last annotation")
        self.undo_button.setObjectName("btn_danger")
        self.undo_button.clicked.connect(self.undo_last_annotation)
        self.undo_button.setEnabled(False)

        self.generate_image_button = QPushButton("Generate annotated board")
        self.generate_image_button.setObjectName("btn_secondary")
        self.generate_image_button.clicked.connect(self.generate_annotated_planche)

        for btn in (self.manage_species_button, self.add_button, self.update_button,
                    self.delete_button, self.undo_button, self.generate_image_button):
            btn.setMaximumHeight(24)

        form_layout.addRow("User:", self.user_input)
        form_layout.addRow("Species:", self.species_combo)
        form_layout.addRow("", self.manage_species_button)
        form_layout.addRow("Count:", self.count_input)
        form_layout.addRow("Comment:", self.comment_input)
        form_layout.addRow("", self.uncertain_box)
        form_layout.addRow("", self.add_button)
        form_layout.addRow("", self.update_button)
        form_layout.addRow("", self.delete_button)
        form_layout.addRow("", self.undo_button)
        form_layout.addRow("", self.generate_image_button)

        self.form_group.setLayout(form_layout)

        self.table_group = QGroupBox("Table")
        table_layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["Row", "Col", "Camera", "Time", "Species", "Count", "Uncertain", "Comment", "User"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.cellClicked.connect(self.on_table_row_clicked)

        table_layout.addWidget(self.table)
        self.table_group.setLayout(table_layout)

        self.table_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        top_forms = QWidget()
        top_forms_layout = QVBoxLayout(top_forms)
        top_forms_layout.setContentsMargins(0, 0, 0, 0)
        top_forms_layout.setSpacing(4)
        top_forms_layout.addWidget(self.info_group)
        top_forms_layout.addWidget(self.form_group)
        top_forms_layout.addStretch()
        top_forms.setMinimumHeight(1)
        self.table_group.setMinimumHeight(1)

        self.right_panel_widget = QSplitter(Qt.Orientation.Vertical)
        self.right_panel_widget.addWidget(top_forms)
        self.right_panel_widget.addWidget(self.table_group)
        for i in range(2):
            self.right_panel_widget.setCollapsible(i, False)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setContentsMargins(18, 12, 18, 12)
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(self.right_panel_widget)
        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(1, False)
        main_splitter.setSizes([800, 400])
        self.right_panel_widget.setMinimumWidth(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(main_splitter, 1)

        self._update_v_label()

    def _build_menu(self):
        file_menu = QMenu(self)

        open_action = QAction("Open drop folder", self)
        open_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_action)

        open_drop_action = QAction("Open drop folder in explorer", self)
        open_drop_action.triggered.connect(self.open_drop_folder_in_explorer)
        file_menu.addAction(open_drop_action)

        open_excel_action = QAction("Open Excel", self)
        open_excel_action.triggered.connect(self.open_excel_file)
        file_menu.addAction(open_excel_action)

        export_crops_action = QAction("Export crops by species", self)
        export_crops_action.triggered.connect(self._exporter_crops)
        file_menu.addAction(export_crops_action)

        manage_species_action = QAction("Manage species", self)
        manage_species_action.triggered.connect(self.manage_species)
        file_menu.addAction(manage_species_action)

        toggle_panel_action = QAction("Hide / show panel", self)
        toggle_panel_action.triggered.connect(self.toggle_right_panel)
        file_menu.addAction(toggle_panel_action)

        self.fichier_button.setMenu(file_menu)

    def _switch_info_tab(self, index):
        self.info_stack.setCurrentIndex(index)
        self.tab_btn_case.setChecked(index == 0)
        self.tab_btn_context.setChecked(index == 1)

    def _update_context_all(self):
        if not self.annotations:
            self.status_message.emit("No annotations to update.", 3000)
            return
        for ann in self.annotations:
            ann["drop_id"] = self.drop_id_value
            ann["campaign"] = self.drop_campaign
            ann["location"] = self.drop_location
            ann["site"] = self.drop_site
            ann["date"] = self.drop_date
            ann["latitude"] = self.drop_latitude
            ann["longitude"] = self.drop_longitude
            ann["habitat"] = self.drop_habitat
            ann["depth"] = self.drop_depth
            ann["visibility"] = self.drop_visibility
        self._save_tabular_outputs_only()
        self.status_message.emit(
            f"Metadata updated for {len(self.annotations)} annotation(s).", 3000
        )

    def _bind_keys(self):
        self.shortcut_prev = QShortcut(QKeySequence(Qt.Key_Up), self)
        self.shortcut_next = QShortcut(QKeySequence(Qt.Key_Down), self)
        self.shortcut_global = QShortcut(QKeySequence(Qt.Key_Escape), self)

        self.shortcut_prev.activated.connect(self.go_prev_in_column)
        self.shortcut_next.activated.connect(self.go_next_in_column)
        self.shortcut_global.activated.connect(self.reset_to_overview)

    def _refresh_species_combo(self):
        self.species_combo.clear()
        for species in self.species_list:
            if species.get("active", True):
                label = f"{species['common_name']} — {species['scientific_name']}"
                self.species_combo.addItem(label, species)
                color_hex = species.get("color", "#CCCCCC")
                bg = QColor(color_hex)
                r, g, b = bg.red(), bg.green(), bg.blue()
                luminance = 0.299 * r + 0.587 * g + 0.114 * b
                fg = QColor("#000000") if luminance > 140 else QColor("#FFFFFF")
                idx = self.species_combo.count() - 1
                self.species_combo.model().item(idx).setBackground(QBrush(bg))
                self.species_combo.model().item(idx).setForeground(QBrush(fg))

    def manage_species(self):
        dialog = SpeciesManagerDialog(self.species_list, self)
        if dialog.exec():
            self.species_list = dialog.get_species_list()
            try:
                save_species(self.species_list)
            except OSError as e:
                QMessageBox.critical(
                    self, "Species list not saved",
                    f"The species database could not be written:\n{e}\n\n"
                    "The changes are active for this session only."
                )
            self._refresh_species_combo()
            self.status_message.emit("Species list updated", 3000)

    def _load_viewer_config(self):
        if not self.viewer_config_path.exists():
            return

        try:
            with open(self.viewer_config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            value = data.get("vertical_guide_ratio", 0.5)
            value = float(value)
            self.vertical_guide_ratio = max(0.0, min(1.0, value))
        except Exception:
            self.vertical_guide_ratio = 0.5

    def _save_viewer_config(self):
        data = {
            "vertical_guide_ratio": self.vertical_guide_ratio
        }
        try:
            with open(self.viewer_config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _update_v_label(self):
        if not self.v_input.hasFocus():
            self.v_input.setText(f"{self.vertical_guide_ratio * 100:.1f}%")

    def _on_zoom_edit(self):
        text = self.zoom_input.text().strip().rstrip('%').strip()
        try:
            target = max(1.0, min(float(text), 5000.0))
            current = self.view.transform().m11() * 100
            if current > 0:
                self.view.scale(target / current, target / current)
        except ValueError:
            pass
        self.update_zoom_label()

    def _on_v_edit(self):
        text = self.v_input.text().strip().rstrip('%').strip()
        try:
            val = max(0.0, min(float(text), 100.0))
            self.vertical_guide_ratio = val / 100.0
            self._save_viewer_config()
            self._draw_annotation_overlay()
        except ValueError:
            pass
        self._update_v_label()

    def _load_drop_metadata(self, folder):
        meta_path = Path(folder) / "drop_metadata.json"
        m = {}
        if meta_path.exists():
            try:
                with open(meta_path, encoding="utf-8") as f:
                    m = json.load(f)
            except Exception:
                pass
        self.campaign_input.setText(str(m.get("campaign", "")))
        self.location_input.setText(str(m.get("location", "")))
        self.site_input.setText(str(m.get("site", "")))
        drop_id_val = m.get("drop_id") or (self.meta.get("drop_id", "") if self.meta else "")
        self.drop_id_input.setText(str(drop_id_val))
        self.date_input.setText(str(m.get("date", "")))
        self.latitude_input.setText(str(m.get("latitude", "")))
        self.longitude_input.setText(str(m.get("longitude", "")))
        self.habitat_input.setText(str(m.get("habitat", "")))
        self.depth_input.setText(str(m.get("depth", "")))
        self.visibility_input.setText(str(m.get("visibility", "")))

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select a drop_XXX folder")
        if not folder:
            return

        folder = Path(folder)
        image_path = folder / "planche_verticale.png"
        metadata_path = folder / "metadata.json"

        if not image_path.exists():
            QMessageBox.critical(self, "Error", f"File not found:\n{image_path}")
            return

        if not metadata_path.exists():
            QMessageBox.critical(self, "Error", f"File not found:\n{metadata_path}")
            return

        try:
            self.meta = load_metadata(metadata_path)
            self.cell_index = build_cell_index(self.meta["cells"])
        except Exception as e:
            QMessageBox.critical(self, "Metadata error", str(e))
            return

        try:
            self.source_image_path = image_path
            self.source_image = Image.open(image_path).convert("RGB")
        except Exception as e:
            QMessageBox.critical(self, "Image error", str(e))
            return

        original_w, original_h = self.source_image.size

        max_preview_pixels = 12_000_000
        pixel_count = original_w * original_h
        if pixel_count > max_preview_pixels:
            preview_scale = (max_preview_pixels / pixel_count) ** 0.5
        else:
            preview_scale = 1.0

        max_long_side = 3500
        preview_scale = min(preview_scale, max_long_side / max(original_w, original_h), 1.0)
        self.preview_scale = preview_scale

        if preview_scale < 1.0:
            preview_w = max(1, int(original_w * preview_scale))
            preview_h = max(1, int(original_h * preview_scale))
            preview_image = self.source_image.resize((preview_w, preview_h), Image.Resampling.LANCZOS)
        else:
            preview_image = self.source_image.copy()

        if not self._load_pil_image_into_scene(preview_image):
            QMessageBox.critical(self, "Error", "Unable to load board preview.")
            return

        cell_w = self.meta.get("cell_width", 9999)
        if cell_w < 400:
            QMessageBox.warning(
                self,
                "Reduced board quality",
                f"Cells in this board are {cell_w}px wide.\n\n"
                f"Below 400px, HQ zoom becomes pixelated and "
                f"species identification may be difficult.\n\n"
                f"Recommendation: videos < 60 min or < 100 extracted frames "
                f"per camera (30s interval, 180s delay).",
            )

        self.folder = folder
        self._load_drop_metadata(folder)
        # Opening a folder must not write to it. Rewriting the outputs here meant
        # regenerating annotations.xlsx from the CSV — silently discarding anything
        # the annotator had corrected in Excel — and it raised PermissionError if the
        # workbook happened to be open. Both files are rewritten on the first change.
        self.annotations = load_existing_annotations(folder)
        self.selected_click_data = None
        self.selected_table_row = None
        self.display_mode = "overview"
        self.current_hq_rect = None
        self.hq_scale = 1.0
        self.hq_display_cache = {}

        self._draw_annotation_overlay()
        self.view.reset_zoom()
        self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        self.update_zoom_label()

        self._clear_info_panel()
        self._clear_form_after_action()
        self._refresh_table()

        self.title_changed.emit(f"FISH ANNOT v2 — {folder.name}")
        if self.annotations:
            self.status_message.emit(
                f"Folder loaded: {folder} | {len(self.annotations)} annotation(s) reloaded",
                5000,
            )
        else:
            self.status_message.emit(f"Folder loaded: {folder}", 4000)

    def _load_pil_image_into_scene(self, pil_image):
        buffer = BytesIO()
        pil_image.save(buffer, format="PNG", optimize=True)

        pixmap = QPixmap()
        ok = pixmap.loadFromData(buffer.getvalue())
        if (not ok) or pixmap.isNull():
            return False

        self.scene.clear()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        w, h = pixmap.width(), pixmap.height()
        self.scene.setSceneRect(-w, -h, 3 * w, 3 * h)
        return True

    def handle_image_click_scene(self, scene_x, scene_y):
        if self.meta is None:
            return

        if self.display_mode == "overview":
            data = compute_cell(scene_x, scene_y, self.meta, self.preview_scale)
            if not data:
                return
            cell = self.cell_index.get((data["row"], data["col"]))
            if cell is None:
                return

            self.selected_click_data = {"cell": cell, **data}
            self._update_info_panel(cell)

        elif self.display_mode == "cell_hq":
            if self.current_hq_rect is None:
                return

            left, top, right, bottom = self.current_hq_rect
            source_x = left + (scene_x / self.hq_scale)
            source_y = top + (scene_y / self.hq_scale)

            data = compute_cell(source_x, source_y, self.meta, 1.0)
            if not data:
                return
            cell = self.cell_index.get((data["row"], data["col"]))
            if cell is None:
                return

            self.selected_click_data = {"cell": cell, **data}
            self._update_info_panel(cell)

    def zoom_on_cell_hq(self):
        if not self.selected_click_data or not self.meta or self.source_image is None:
            QMessageBox.warning(self, "No cell selected", "Click on a cell first.")
            return

        row = self.selected_click_data["row"]
        col = self.selected_click_data["col"]

        left = int(self.meta["left_label_width"] + col * self.meta["cell_width"])
        top = int(self.meta["top_header_height"] + row * self.meta["cell_height"])
        right = int(left + self.meta["cell_width"])
        bottom = int(top + self.meta["cell_height"])

        viewport_w = max(400, self.view.viewport().width() - 20)
        viewport_h = max(300, self.view.viewport().height() - 20)

        # The viewport size is part of the key: the cached image is rendered for a
        # given viewport, so after the window is resized a cell keyed on (row, col)
        # alone would come back at the old scale.
        key = (row, col, viewport_w, viewport_h)

        if key in self.hq_display_cache:
            display = self.hq_display_cache[key]
        else:
            try:
                crop = self.source_image.crop((left, top, right, bottom))
            except Exception as e:
                QMessageBox.critical(self, "HQ zoom error", str(e))
                return

            cell_w, cell_h = crop.size
            display_scale = min(viewport_w / cell_w, viewport_h / cell_h)
            display_scale = max(display_scale, 1.0)

            display_w = max(1, int(cell_w * display_scale))
            display_h = max(1, int(cell_h * display_scale))

            display = crop.resize((display_w, display_h), Image.Resampling.LANCZOS)
            self.hq_display_cache[key] = display

        cell_w = self.meta["cell_width"]
        self.hq_scale = display.size[0] / cell_w

        if not self._load_pil_image_into_scene(display):
            QMessageBox.critical(self, "Error", "Unable to load HQ zoom.")
            return

        self.display_mode = "cell_hq"
        self.current_hq_rect = (left, top, right, bottom)

        self._draw_annotation_overlay()
        self.view.reset_zoom()
        self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        self.update_zoom_label()
        self.status_message.emit(f"HQ cell zoom active — row {row}, col {col}", 3000)

    def reset_to_overview(self):
        if self.source_image is None:
            return

        original_w, original_h = self.source_image.size
        pixel_count = original_w * original_h
        max_preview_pixels = 12_000_000

        if pixel_count > max_preview_pixels:
            preview_scale = (max_preview_pixels / pixel_count) ** 0.5
        else:
            preview_scale = 1.0

        max_long_side = 3500
        preview_scale = min(preview_scale, max_long_side / max(original_w, original_h), 1.0)
        self.preview_scale = preview_scale

        if preview_scale < 1.0:
            preview_w = max(1, int(original_w * preview_scale))
            preview_h = max(1, int(original_h * preview_scale))
            preview = self.source_image.resize((preview_w, preview_h), Image.Resampling.LANCZOS)
        else:
            preview = self.source_image.copy()

        if not self._load_pil_image_into_scene(preview):
            QMessageBox.critical(self, "Error", "Unable to return to overview.")
            return

        self.display_mode = "overview"
        self.current_hq_rect = None
        self.hq_scale = 1.0
        self.vertical_guide_item = None

        self._draw_annotation_overlay()
        self.view.reset_zoom()
        self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        self.update_zoom_label()

    def go_prev_in_column(self):
        if self.selected_click_data is None or self.meta is None:
            return

        row = self.selected_click_data["row"]
        col = self.selected_click_data["col"]
        new_row = row - 1

        if (new_row, col) not in self.cell_index:
            return

        cell = self.cell_index[(new_row, col)]
        self.selected_click_data = {
            "row": new_row,
            "col": col,
            "cell": cell,
            "x_image": self.meta["left_label_width"] + col * self.meta["cell_width"] + (self.meta["cell_width"] / 2),
            "y_image": self.meta["top_header_height"] + new_row * self.meta["cell_height"] + (self.meta["cell_height"] / 2),
            "x_data": col * self.meta["cell_width"] + (self.meta["cell_width"] / 2),
            "y_data": new_row * self.meta["cell_height"] + (self.meta["cell_height"] / 2),
            "x_in_cell": self.meta["cell_width"] / 2,
            "y_in_cell": self.meta["cell_height"] / 2,
        }
        self._update_info_panel(cell)

        if self.display_mode == "cell_hq":
            self.zoom_on_cell_hq()

    def go_next_in_column(self):
        if self.selected_click_data is None or self.meta is None:
            return

        row = self.selected_click_data["row"]
        col = self.selected_click_data["col"]
        new_row = row + 1

        if (new_row, col) not in self.cell_index:
            return

        cell = self.cell_index[(new_row, col)]
        self.selected_click_data = {
            "row": new_row,
            "col": col,
            "cell": cell,
            "x_image": self.meta["left_label_width"] + col * self.meta["cell_width"] + (self.meta["cell_width"] / 2),
            "y_image": self.meta["top_header_height"] + new_row * self.meta["cell_height"] + (self.meta["cell_height"] / 2),
            "x_data": col * self.meta["cell_width"] + (self.meta["cell_width"] / 2),
            "y_data": new_row * self.meta["cell_height"] + (self.meta["cell_height"] / 2),
            "x_in_cell": self.meta["cell_width"] / 2,
            "y_in_cell": self.meta["cell_height"] / 2,
        }
        self._update_info_panel(cell)

        if self.display_mode == "cell_hq":
            self.zoom_on_cell_hq()

    def update_zoom_label(self):
        transform = self.view.transform()
        zoom_percent = transform.m11() * 100
        if not self.zoom_input.hasFocus():
            self.zoom_input.setText(f"{zoom_percent:.0f}%")
        self._update_v_label()

    def toggle_right_panel(self):
        self.right_panel_visible = not self.right_panel_visible
        self.right_panel_widget.setVisible(self.right_panel_visible)
        self.toggle_panel_button.setText("Hide panel" if self.right_panel_visible else "Show panel")

    def _update_info_panel(self, cell):
        self.info_drop.setText(str(self.meta.get("drop_id", "-")))
        self.info_row.setText(str(cell.get("row", "-")))
        self.info_col.setText(str(cell.get("col", "-")))
        self.info_camera.setText(str(cell.get("camera_id", "-")))
        self.info_time_seconds.setText(str(cell.get("time_seconds", "-")))
        self.info_time_label.setText(str(cell.get("time_label", "-")))
        self.info_image_id.setText(str(cell.get("image_id", "-")))
        self.info_image_file.setText(str(cell.get("image_file", "-")))

    def _clear_info_panel(self):
        self.info_drop.setText("-")
        self.info_row.setText("-")
        self.info_col.setText("-")
        self.info_camera.setText("-")
        self.info_time_seconds.setText("-")
        self.info_time_label.setText("-")
        self.info_image_id.setText("-")
        self.info_image_file.setText("-")

    def add_annotation(self):
        if self.folder is None or self.meta is None:
            QMessageBox.warning(self, "No folder", "Open a drop folder first.")
            return

        if self.selected_click_data is None:
            QMessageBox.warning(self, "No cell clicked", "Click on the board first.")
            return

        if self.species_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Missing species", "No species selected.")
            return

        species = self.species_combo.currentData()
        cell = self.selected_click_data["cell"]

        annotation = {
            # The Metadata tab wins over metadata.json: "Update metadata" rewrites
            # every existing row with it, so taking the board's own drop_id here
            # would leave new annotations disagreeing with the ones already saved.
            "drop_id": self.drop_id_value or self.meta.get("drop_id", ""),
            "row": cell.get("row", ""),
            "col": cell.get("col", ""),
            "camera_id": cell.get("camera_id", ""),
            "frame_rank": cell.get("frame_rank", ""),
            "time_seconds": cell.get("time_seconds", ""),
            "time_label": cell.get("time_label", ""),
            "image_id": cell.get("image_id", ""),
            "image_file": cell.get("image_file", ""),
            "x_image": self.selected_click_data["x_image"],
            "y_image": self.selected_click_data["y_image"],
            "x_data": self.selected_click_data["x_data"],
            "y_data": self.selected_click_data["y_data"],
            "x_in_cell": self.selected_click_data["x_in_cell"],
            "y_in_cell": self.selected_click_data["y_in_cell"],
            "species_common_name": species.get("common_name", ""),
            "species_scientific_name": species.get("scientific_name", ""),
            "family": species.get("family", ""),
            "species_color": species.get("color", "#CCCCCC"),
            "count": self.count_input.value(),
            "comment": self.comment_input.text().strip(),
            "is_uncertain": self.uncertain_box.isChecked(),
            "user": self.user_input.text().strip(),
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "campaign": self.drop_campaign,
            "location": self.drop_location,
            "site": self.drop_site,
            "date": self.drop_date,
            "latitude": self.drop_latitude,
            "longitude": self.drop_longitude,
            "habitat": self.drop_habitat,
            "depth": self.drop_depth,
            "visibility": self.drop_visibility,
        }

        self.annotations.append(annotation)
        self._save_tabular_outputs_only()
        self._draw_annotation_overlay()
        self._refresh_table()
        self._clear_form_after_action()
        self.undo_button.setEnabled(len(self.annotations) > 0)
        self.status_message.emit("Annotation added", 3000)

    def on_table_row_clicked(self, row, column):
        if row < 0 or row >= len(self.annotations):
            return

        self.selected_table_row = row
        ann = self.annotations[row]

        species_index = self._find_species_index(
            ann.get("species_common_name", ""),
            ann.get("species_scientific_name", ""),
        )
        if species_index >= 0:
            self.species_combo.setCurrentIndex(species_index)

        try:
            self.count_input.setValue(int(ann.get("count", 1)))
        except Exception:
            self.count_input.setValue(1)

        self.comment_input.setText(str(ann.get("comment", "")))
        self.uncertain_box.setChecked(bool(ann.get("is_uncertain", False)))
        self.user_input.setText(str(ann.get("user", "")))

        self.update_button.setEnabled(True)
        self.delete_button.setEnabled(True)

        fake_cell = {
            "row": ann.get("row", "-"),
            "col": ann.get("col", "-"),
            "camera_id": ann.get("camera_id", "-"),
            "time_seconds": ann.get("time_seconds", "-"),
            "time_label": ann.get("time_label", "-"),
            "image_id": ann.get("image_id", "-"),
            "image_file": ann.get("image_file", "-"),
        }
        self._update_info_panel(fake_cell)

    def _find_species_index(self, common_name, scientific_name):
        for i in range(self.species_combo.count()):
            data = self.species_combo.itemData(i)
            if not data:
                continue
            if (
                data.get("common_name", "") == common_name
                and data.get("scientific_name", "") == scientific_name
            ):
                return i
        return -1

    def update_annotation(self):
        if self.selected_table_row is None:
            QMessageBox.warning(self, "No selection", "Select an annotation in the table first.")
            return

        if self.selected_table_row < 0 or self.selected_table_row >= len(self.annotations):
            return

        species = self.species_combo.currentData()
        if not species:
            return

        ann = self.annotations[self.selected_table_row]
        ann["species_common_name"] = species.get("common_name", "")
        ann["species_scientific_name"] = species.get("scientific_name", "")
        ann["family"] = species.get("family", "")
        ann["species_color"] = species.get("color", "#CCCCCC")
        ann["count"] = self.count_input.value()
        ann["comment"] = self.comment_input.text().strip()
        ann["is_uncertain"] = self.uncertain_box.isChecked()
        ann["user"] = self.user_input.text().strip()
        ann["timestamp"] = datetime.datetime.now().isoformat(timespec="seconds")
        ann["campaign"] = self.drop_campaign
        ann["location"] = self.drop_location
        ann["site"] = self.drop_site
        ann["date"] = self.drop_date
        ann["latitude"] = self.drop_latitude
        ann["longitude"] = self.drop_longitude
        ann["habitat"] = self.drop_habitat
        ann["depth"] = self.drop_depth
        ann["visibility"] = self.drop_visibility

        self._save_tabular_outputs_only()
        self._draw_annotation_overlay()
        self._refresh_table()
        self._clear_form_after_action()
        self.status_message.emit("Annotation updated", 3000)

    def delete_selected_annotation(self):
        if self.selected_table_row is None:
            QMessageBox.warning(self, "No selection", "Select an annotation in the table first.")
            return

        if self.selected_table_row < 0 or self.selected_table_row >= len(self.annotations):
            return

        del self.annotations[self.selected_table_row]
        self._save_tabular_outputs_only()
        self._draw_annotation_overlay()
        self._refresh_table()
        self._clear_form_after_action()
        self.undo_button.setEnabled(len(self.annotations) > 0)
        self.status_message.emit("Annotation deleted", 3000)

    def undo_last_annotation(self):
        if not self.annotations:
            return

        self.annotations.pop()
        self._save_tabular_outputs_only()
        self._draw_annotation_overlay()
        self._refresh_table()
        self._clear_form_after_action()
        self.undo_button.setEnabled(len(self.annotations) > 0)
        self.status_message.emit("Last annotation undone", 3000)

    def _clear_form_after_action(self):
        self.comment_input.clear()
        self.count_input.setValue(1)
        self.uncertain_box.setChecked(False)
        self.selected_table_row = None
        self.update_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.table.clearSelection()

    def _refresh_table(self):
        self.table.setRowCount(len(self.annotations))

        for row_idx, ann in enumerate(self.annotations):
            values = [
                str(ann.get("row", "")),
                str(ann.get("col", "")),
                str(ann.get("camera_id", "")),
                str(ann.get("time_label", "")),
                str(ann.get("species_common_name", "")),
                str(ann.get("count", "")),
                "Yes" if bool(ann.get("is_uncertain", False)) else "No",
                str(ann.get("comment", "")),
                str(ann.get("user", "")),
            ]

            for col_idx, value in enumerate(values):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(value))

        self.table.resizeColumnsToContents()
        self.undo_button.setEnabled(len(self.annotations) > 0)

    def _save_tabular_outputs_only(self):
        if self.folder is None:
            return

        try:
            save_csv_xlsx(self.annotations, self.folder)
        except PermissionError:
            QMessageBox.warning(
                self,
                "Excel file open",
                "The file annotations.xlsx is open.\nClose Excel to allow saving."
            )
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))

    def generate_annotated_planche(self):
        if self.folder is None:
            QMessageBox.warning(self, "No folder", "Open a drop folder first.")
            return

        try:
            draw_annotations(
                self.folder / "planche_verticale.png",
                self.annotations,
                self.folder / "planche_annotated.png",
            )
            self.status_message.emit("Annotated board generated", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Image generation error", str(e))

    def _draw_annotation_overlay(self):
        if self.pixmap_item is None:
            return

        for item in list(self.scene.items()):
            if item is self.pixmap_item:
                continue
            self.scene.removeItem(item)

        for ann in self.annotations:
            try:
                src_x = float(ann.get("x_image", 0))
                src_y = float(ann.get("y_image", 0))
            except Exception:
                continue

            if self.display_mode == "overview":
                x = src_x * self.preview_scale
                y = src_y * self.preview_scale
            else:
                if self.current_hq_rect is None:
                    continue
                left, top, right, bottom = self.current_hq_rect
                if not (left <= src_x <= right and top <= src_y <= bottom):
                    continue
                x = (src_x - left) * self.hq_scale
                y = (src_y - top) * self.hq_scale

            color = QColor(str(ann.get("species_color", "#FF0000")))
            pen = QPen(QColor("black"))
            brush = QBrush(color)

            radius = 6
            ellipse = QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)
            ellipse.setPen(pen)
            ellipse.setBrush(brush)
            self.scene.addItem(ellipse)

            label = str(ann.get("species_common_name", ""))
            count = ann.get("count", 1)
            try:
                if int(count) > 1:
                    label = f"{label} x{int(count)}"
            except Exception:
                pass

            if bool(ann.get("is_uncertain", False)):
                label = f"? {label}"

            text_item = QGraphicsSimpleTextItem(label)
            text_item.setBrush(QBrush(color))
            text_item.setPos(x + 10, y - 10)
            self.scene.addItem(text_item)

        self._draw_vertical_guide_if_needed()

    def _draw_vertical_guide_if_needed(self):
        self.vertical_guide_item = None

        if self.display_mode != "cell_hq" or self.pixmap_item is None:
            self._update_v_label()
            return

        pixmap = self.pixmap_item.pixmap()
        w = pixmap.width()
        h = pixmap.height()

        x = self.vertical_guide_ratio * w

        pen = QPen(QColor("#FF0033"))
        pen.setWidth(3)

        self.vertical_guide_item = QGraphicsLineItem(x, 0, x, h)
        self.vertical_guide_item.setPen(pen)
        self.scene.addItem(self.vertical_guide_item)
        self._update_v_label()

    def update_vertical_guide_from_scene_x(self, scene_x):
        if self.display_mode != "cell_hq" or self.pixmap_item is None:
            return

        w = self.pixmap_item.pixmap().width()
        if w <= 0:
            return

        self.vertical_guide_ratio = max(0.0, min(1.0, scene_x / w))
        self._save_viewer_config()
        self._draw_annotation_overlay()

    def open_drop_folder_in_explorer(self):
        if self.folder is None:
            QMessageBox.warning(self, "No folder", "Open a drop folder first.")
            return
        os.startfile(str(self.folder))

    def _exporter_crops(self):
        if self.folder is None:
            QMessageBox.warning(self, "No folder", "Open a drop folder first.")
            return

        if not self.annotations:
            QMessageBox.warning(self, "No annotations", "No annotations to export.")
            return

        dossier_sortie = QFileDialog.getExistingDirectory(
            self, "Choose output folder for crops"
        )
        if not dossier_sortie:
            return

        self.status_message.emit("Exporting crops…", 0)
        self.setEnabled(False)

        try:
            resultats = export_crops_par_espece(
                self.annotations,
                self.folder,
                dossier_sortie,
            )
        except Exception as e:
            self.setEnabled(True)
            QMessageBox.critical(self, "Crop export error", str(e))
            self.status_message.emit("Error during crop export", 4000)
            return

        self.setEnabled(True)
        self.status_message.emit("Crop export complete", 4000)

        QMessageBox.information(
            self,
            "Export complete",
            f"Export complete.\n\n"
            f"{resultats['n_bbox']} crops exported using a detection box.\n"
            f"{resultats['n_fallback']} crops exported as fallback (no bbox found).\n"
            f"{resultats['n_trop_petit']} crops ignored (too small < {exporter.MIN_CROP_PX} px).\n"
            f"{resultats['n_ignore']} annotations ignored (source frame not found).\n\n"
            f"Folder: {dossier_sortie}",
        )

    def open_excel_file(self):
        if self.folder is None:
            QMessageBox.warning(self, "No folder", "Open a drop folder first.")
            return

        excel_path = self.folder / "annotations.xlsx"
        if not excel_path.exists():
            QMessageBox.warning(self, "Excel file not found", "The file annotations.xlsx does not exist yet.")
            return

        os.startfile(str(excel_path))
