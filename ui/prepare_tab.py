import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.planche_builder import build_from_videos, build_from_images


# ──────────────────────────────────────────────────────────────────────────────
# Worker thread
# ──────────────────────────────────────────────────────────────────────────────

class BuildWorker(QThread):
    progress   = Signal(int)
    log        = Signal(str)
    # Deliberately not called "finished": QThread already owns a signal by that name,
    # and redefining it here shadows the one Qt emits when the thread really ends.
    build_done = Signal(bool, str)   # success, message

    def __init__(self, mode, paths, params, output_dir, drop_id):
        super().__init__()
        self.mode       = mode        # "videos" | "images"
        self.paths      = paths
        self.params     = params
        self.output_dir = output_dir
        self.drop_id    = drop_id
        self._abort     = False

    def abort(self):
        self._abort = True

    def run(self):
        try:
            fn = build_from_videos if self.mode == "videos" else build_from_images
            n_segs, out_path = fn(
                self.paths,
                self.params,
                self.output_dir,
                self.drop_id,
                on_progress=lambda p: self.progress.emit(p),
                on_log=lambda m: self.log.emit(m),
                check_abort=lambda: self._abort,
            )
            if self._abort:
                self.build_done.emit(False, "Annulé.")
            else:
                self.build_done.emit(True, f"{n_segs} segment(s) → {out_path}")
        except Exception as e:
            self.build_done.emit(False, str(e))


# ──────────────────────────────────────────────────────────────────────────────
# File list widget (shared between modes)
# ──────────────────────────────────────────────────────────────────────────────

class FileListWidget(QWidget):
    def __init__(self, title, filters):
        super().__init__()
        self._filters = filters

        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.btn_add    = QPushButton("+ Add files")
        self.btn_remove = QPushButton("− Remove")
        self.btn_clear  = QPushButton("Clear all")
        for btn in (self.btn_add, self.btn_remove, self.btn_clear):
            btn.setMaximumHeight(24)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_clear)
        layout.addLayout(btn_row)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(group)

        self.btn_add.clicked.connect(self._add)
        self.btn_remove.clicked.connect(self._remove)
        self.btn_clear.clicked.connect(self.list_widget.clear)

    def _add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select files", "", self._filters)
        for p in paths:
            if not any(self.list_widget.item(i).data(Qt.UserRole) == p
                       for i in range(self.list_widget.count())):
                item = QListWidgetItem(Path(p).name)
                item.setData(Qt.UserRole, p)
                item.setToolTip(p)
                self.list_widget.addItem(item)

    def _remove(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def paths(self):
        return [
            Path(self.list_widget.item(i).data(Qt.UserRole))
            for i in range(self.list_widget.count())
        ]


# ──────────────────────────────────────────────────────────────────────────────
# PrepareTab
# ──────────────────────────────────────────────────────────────────────────────

class PrepareTab(QWidget):
    def __init__(self):
        super().__init__()
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        # ── Mode selector ────────────────────────────────────────────────────
        self.btn_mode_video = QPushButton("From videos")
        self.btn_mode_video.setObjectName("tab_btn")
        self.btn_mode_video.setCheckable(True)
        self.btn_mode_video.setChecked(True)
        self.btn_mode_video.setMaximumHeight(26)

        self.btn_mode_image = QPushButton("From images")
        self.btn_mode_image.setObjectName("tab_btn")
        self.btn_mode_image.setCheckable(True)
        self.btn_mode_image.setChecked(False)
        self.btn_mode_image.setMaximumHeight(26)

        mode_bar = QHBoxLayout()
        mode_bar.setSpacing(2)
        mode_bar.setContentsMargins(0, 4, 0, 4)
        mode_bar.addWidget(self.btn_mode_video)
        mode_bar.addWidget(self.btn_mode_image)
        mode_bar.addStretch()

        self.btn_mode_video.clicked.connect(lambda: self._switch_mode(0))
        self.btn_mode_image.clicked.connect(lambda: self._switch_mode(1))

        # ── File lists ───────────────────────────────────────────────────────
        self.file_list_video = FileListWidget(
            "Video files",
            "Videos (*.mp4 *.MP4 *.mov *.MOV *.avi *.AVI *.mkv *.MKV);;All files (*)"
        )
        self.file_list_image = FileListWidget(
            "Image files",
            "Images (*.jpg *.JPG *.jpeg *.JPEG *.png *.PNG *.tif *.tiff);;All files (*)"
        )

        self.file_stack = QStackedWidget()
        self.file_stack.addWidget(self.file_list_video)
        self.file_stack.addWidget(self.file_list_image)

        # ── Parameters — video ───────────────────────────────────────────────
        self.p_start_delay   = QSpinBox(); self.p_start_delay.setRange(0, 3600); self.p_start_delay.setSuffix(" s"); self.p_start_delay.setValue(0)
        self.p_interval      = QDoubleSpinBox(); self.p_interval.setRange(0.1, 300); self.p_interval.setSuffix(" s"); self.p_interval.setValue(1.0); self.p_interval.setSingleStep(0.5)
        self.p_frames_seg    = QSpinBox(); self.p_frames_seg.setRange(1, 1000); self.p_frames_seg.setValue(100)
        self.p_cell_w_vid    = QSpinBox(); self.p_cell_w_vid.setRange(64, 3840); self.p_cell_w_vid.setSuffix(" px"); self.p_cell_w_vid.setValue(640)
        self.p_cell_h_vid    = QSpinBox(); self.p_cell_h_vid.setRange(64, 2160); self.p_cell_h_vid.setSuffix(" px"); self.p_cell_h_vid.setValue(360)
        self.p_save_frames   = QCheckBox("Save source frames (enables crop export)")
        self.p_save_frames.setChecked(False)

        vid_form = QFormLayout()
        vid_form.setSpacing(4)
        vid_form.addRow("Start delay:",        self.p_start_delay)
        vid_form.addRow("Frame interval:",     self.p_interval)
        vid_form.addRow("Frames / segment:",   self.p_frames_seg)
        vid_form.addRow("Cell width:",         self.p_cell_w_vid)
        vid_form.addRow("Cell height:",        self.p_cell_h_vid)
        vid_form.addRow("",                    self.p_save_frames)

        vid_param_widget = QGroupBox("Parameters")
        vid_param_widget.setLayout(vid_form)

        # ── Parameters — image ───────────────────────────────────────────────
        self.p_n_columns     = QSpinBox(); self.p_n_columns.setRange(1, 20); self.p_n_columns.setValue(5)
        self.p_imgs_per_seg  = QSpinBox(); self.p_imgs_per_seg.setRange(1, 200); self.p_imgs_per_seg.setValue(20)
        self.p_cell_w_img    = QSpinBox(); self.p_cell_w_img.setRange(64, 3840); self.p_cell_w_img.setSuffix(" px"); self.p_cell_w_img.setValue(640)
        self.p_cell_h_img    = QSpinBox(); self.p_cell_h_img.setRange(64, 2160); self.p_cell_h_img.setSuffix(" px"); self.p_cell_h_img.setValue(360)

        img_form = QFormLayout()
        img_form.setSpacing(4)
        img_form.addRow("Columns (nx):",       self.p_n_columns)
        img_form.addRow("Rows / segment (ny):", self.p_imgs_per_seg)
        img_form.addRow("Cell width:",         self.p_cell_w_img)
        img_form.addRow("Cell height:",        self.p_cell_h_img)

        img_param_widget = QGroupBox("Parameters")
        img_param_widget.setLayout(img_form)

        self.param_stack = QStackedWidget()
        self.param_stack.addWidget(vid_param_widget)
        self.param_stack.addWidget(img_param_widget)

        # ── Left column: files + params ──────────────────────────────────────
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addLayout(mode_bar)
        left_layout.addWidget(self.file_stack, 3)
        left_layout.addWidget(self.param_stack, 2)

        # ── Output section ───────────────────────────────────────────────────
        self.drop_id_input = QLineEdit()
        self.drop_id_input.setPlaceholderText("e.g.  DFDF1-10")

        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Output folder…")
        self.output_input.setReadOnly(True)

        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.setMaximumHeight(26)
        self.btn_browse.clicked.connect(self._browse_output)

        output_row = QHBoxLayout()
        output_row.addWidget(self.output_input, 1)
        output_row.addWidget(self.btn_browse)

        output_form = QFormLayout()
        output_form.setSpacing(4)
        output_form.addRow("Drop ID:", self.drop_id_input)
        output_form.addRow("Output:",  output_row)

        output_group = QGroupBox("Output")
        output_group.setLayout(output_form)

        # ── Generate / Cancel buttons ────────────────────────────────────────
        self.btn_generate = QPushButton("Generate")
        self.btn_generate.setObjectName("btn_primary")
        self.btn_generate.setMinimumHeight(30)
        self.btn_generate.clicked.connect(self._generate)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn_danger")
        self.btn_cancel.setMinimumHeight(30)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel)

        self.btn_open = QPushButton("Open output folder")
        self.btn_open.setObjectName("btn_secondary")
        self.btn_open.setMinimumHeight(30)
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self._open_output)

        action_row = QHBoxLayout()
        action_row.addWidget(self.btn_generate, 1)
        action_row.addWidget(self.btn_cancel)
        action_row.addWidget(self.btn_open)

        # ── Progress ─────────────────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumHeight(18)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(180)
        self.log_area.setStyleSheet(
            "QTextEdit { background:#1e1e1e; color:#d4d4d4;"
            " font-family:Consolas; font-size:9pt; border:none; }"
        )

        progress_group = QGroupBox("Progress")
        pg_layout = QVBoxLayout(progress_group)
        pg_layout.addWidget(self.progress_bar)
        pg_layout.addWidget(self.log_area)

        # ── Right column: output + progress ──────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(output_group)
        right_layout.addLayout(action_row)
        right_layout.addWidget(progress_group, 1)
        right_layout.addStretch()

        # ── Main splitter ────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([500, 400])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 12, 18, 12)
        outer.addWidget(splitter, 1)

        self._last_output_path = None

    # ── Mode switch ──────────────────────────────────────────────────────────

    def _switch_mode(self, index):
        self.file_stack.setCurrentIndex(index)
        self.param_stack.setCurrentIndex(index)
        self.btn_mode_video.setChecked(index == 0)
        self.btn_mode_image.setChecked(index == 1)

    # ── Browse output ────────────────────────────────────────────────────────

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select output folder")
        if folder:
            self.output_input.setText(folder)

    # ── Generate ─────────────────────────────────────────────────────────────

    def _generate(self):
        mode = "videos" if self.file_stack.currentIndex() == 0 else "images"
        file_list = self.file_list_video if mode == "videos" else self.file_list_image

        paths = file_list.paths()
        if not paths:
            QMessageBox.warning(self, "No files", "Add at least one file.")
            return

        drop_id = self.drop_id_input.text().strip()
        if not drop_id:
            QMessageBox.warning(self, "Drop ID missing", "Enter a drop ID.")
            return

        output_dir = self.output_input.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "No output folder", "Select an output folder.")
            return

        out_drop = Path(output_dir) / drop_id
        if out_drop.exists():
            existing_segs = sorted(q for q in out_drop.glob("seg_*") if q.is_dir())
            detail = (
                f"\n\nIts {len(existing_segs)} existing seg_XXX folder(s) will be "
                f"deleted and rebuilt — anything saved inside them is lost."
                if existing_segs else ""
            )
            r = QMessageBox.question(
                self, "Folder exists",
                f"The folder already exists:\n{out_drop}{detail}\n\nContinue?",
                QMessageBox.Yes | QMessageBox.No
            )
            if r != QMessageBox.Yes:
                return
            # Without this the new run merges into the old one: a previous, longer
            # run leaves seg_007+ behind and the Annotate tab still opens them.
            for seg in existing_segs:
                shutil.rmtree(seg, ignore_errors=True)

        if mode == "videos":
            params = {
                "start_delay":    self.p_start_delay.value(),
                "frame_interval": self.p_interval.value(),
                "frames_per_seg": self.p_frames_seg.value(),
                "cell_width":     self.p_cell_w_vid.value(),
                "cell_height":    self.p_cell_h_vid.value(),
                "save_frames":    self.p_save_frames.isChecked(),
            }
        else:
            params = {
                "n_columns":     self.p_n_columns.value(),
                "images_per_seg": self.p_imgs_per_seg.value(),
                "cell_width":    self.p_cell_w_img.value(),
                "cell_height":   self.p_cell_h_img.value(),
            }

        self.log_area.clear()
        self.progress_bar.setValue(0)
        self.btn_generate.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_open.setEnabled(False)
        self._last_output_path = str(out_drop)

        self._worker = BuildWorker(mode, paths, params, output_dir, drop_id)
        self._worker.progress.connect(self.progress_bar.setValue)
        self._worker.log.connect(self._append_log)
        self._worker.build_done.connect(self._on_finished)
        self._worker.start()

    # ── Cancel ───────────────────────────────────────────────────────────────

    def _cancel(self):
        if self._worker and self._worker.isRunning():
            self._worker.abort()

    # ── Finished ─────────────────────────────────────────────────────────────

    def shutdown(self):
        """Stop a running build and wait for it — called when the window closes.

        Qt aborts the process when a QThread is destroyed while still running.
        """
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait(10000)

    def _on_finished(self, success, message):
        self.btn_generate.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if success:
            self.btn_open.setEnabled(True)
            self._append_log(f"\n✓ {message}")
            self.progress_bar.setValue(100)
        else:
            self._append_log(f"\n✗ Erreur : {message}")
            QMessageBox.critical(self, "Error", message)

    # ── Open output folder ────────────────────────────────────────────────────

    def _open_output(self):
        if self._last_output_path and Path(self._last_output_path).exists():
            os.startfile(self._last_output_path)

    # ── Log ──────────────────────────────────────────────────────────────────

    def _append_log(self, msg):
        self.log_area.append(msg)
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())
