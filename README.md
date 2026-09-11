# FISH Annot

**Manual fish species annotation tool**
Build composite image boards from underwater videos, then review and annotate fish species on them (DOP drop-camera protocol, Martinique).

---

## Overview

FISH Annot is a standalone Windows desktop application organised in two tabs:

| Tab | Role |
|---|---|
| **Prepare** | Turn raw drop-camera videos (or loose images) into composite grid boards — one board per segment, with the `metadata.json` descriptor the Annotate tab needs |
| **Annotate** | Browse a board cell by cell, click on fish, assign a species, and export structured annotation tables |

Version 2 is self-contained: it produces its own boards, so no external pipeline is required to use it. Boards produced by other tools are still accepted, as long as they follow the `metadata.json` schema documented below.

**There is no machine learning in this application.** It is a manual data-entry tool.

---

## Requirements

- Windows 10 or 11 (64-bit)
- No Python installation required when using the installer

---

## Installation

Download **`FISH_Annot_Setup_v2.0.0.exe`** from the Zenodo record and run it: <https://doi.org/10.5281/zenodo.22699643>

The installer bundles the application and all its dependencies.

### Running from source (optional)

```bash
conda create -n fish_annot python=3.10
conda activate fish_annot
pip install -r requirements.txt
python main.py
```

---

## Tab 1 — Prepare

Select a mode with the **From videos** / **From images** buttons, add your files, set the parameters, then click **Build**. Processing runs in a background thread with a progress bar, a live log and a **Cancel** button.

### Mode: From videos

Each video is one **column** of the board — i.e. one camera of the drop. Frames are sampled at a fixed time interval and stacked as rows.

| Parameter | Default | Meaning |
|---|---|---|
| Start delay | `0 s` | Time skipped at the beginning of each video (descent, surface noise) |
| Frame interval | `1.0 s` | Time between two sampled frames |
| Frames / segment | `100` | Number of rows per board — a longer video produces several segments |
| Cell width / height | `640 x 360 px` | Size of one cell in the composite board |
| Save source frames | off | Also writes each sampled frame at **its original resolution** as `{camera_id}_frames/frame_XXXXXX.jpg` — **required for crop export** in the Annotate tab. Costs disk space, not memory |

Accepted formats: `.mp4`, `.mov`, `.avi`, `.mkv`. Frame skipping uses OpenCV `grab()`, which is markedly faster than seeking on H.264 footage.

### Mode: From images

Images are laid out in reading order (left to right, then top to bottom).

| Parameter | Default | Meaning |
|---|---|---|
| Columns (nx) | `5` | Number of columns of the board |
| Rows / segment (ny) | `20` | Number of rows per segment — so `nx x ny` images per board |
| Cell width / height | `640 x 360 px` | Size of one cell in the composite board |

Accepted formats: `.jpg`, `.png`, `.tif`.

### Output

Set a **Drop ID** and an **Output** folder. The build writes:

```
<output>/<drop_id>/
├── seg_001/
│   ├── planche_verticale.png        # composite board
│   ├── metadata.json                # grid descriptor
│   └── {camera_id}_frames/          # only if "Save source frames" is ticked
│       └── frame_000000.jpg
├── seg_002/
└── ...
```

Each `seg_XXX/` folder is directly loadable in the Annotate tab.

---

## Tab 2 — Annotate

### 1 — Open a drop folder

Click **File → Open drop folder** and select a `seg_XXX/` folder. It must contain:
- `planche_verticale.png` — the composite grid image
- `metadata.json` — the grid structure descriptor

### 2 — Navigate the grid

The composite image opens in overview mode, with a grid overlay.

| Action | Effect |
|---|---|
| Click on a cell | Select it — cell metadata appears in the right panel |
| Double-click on a cell | Zoom into it (HQ view) + open annotation form |
| `↑` / `↓` | Previous / next row within the current column |
| `Escape` | Return to overview |
| Scroll wheel | Zoom in / out (~5 % per notch) |
| Click and drag | Pan the image |
| **Overview** button | Fit the full grid to the window |
| **HQ Cell Zoom** button | Zoom into the selected cell |
| **Hide panel** button | Toggle the right annotation panel |

A draggable **vertical guide** (blue line) helps split the cell into left / right halves for visual reference. Its position is saved per session in `config/viewer_config.json`.

### 3 — Annotate

Once in HQ cell zoom, click anywhere on the organism to annotate:

1. Select the **species** from the colour-coded dropdown.
2. Set the **count** (default: 1).
3. Tick **Uncertain** if the identification is ambiguous.
4. Optionally add a free-text **comment**.
5. Click **Add** to record the annotation.

Annotations are **auto-saved** to `annotations.csv` and `annotations.xlsx` after each action.

To edit or delete an existing annotation, select it in the annotation table and use the **Edit** / **Delete** buttons.

### 4 — Drop metadata

Switch to the **Metadata** tab in the right panel to record drop-level context:

Campaign, Location, Site, Drop ID, Date, GPS coordinates, Habitat, Depth, Visibility.

Click **Update metadata** to propagate these values to all existing annotations.

### 5 — Outputs

| Action | Menu / Button | Output |
|---|---|---|
| Auto-save | — (automatic) | `annotations.csv`, `annotations.xlsx` |
| Annotated board | **Generate annotated board** | `planche_annotated.png` |
| Crops by species | **File → Export crops by species** | `crops/<scientific_name>/*.jpg` |

---

## Input format

```
<seg_folder>/
├── planche_verticale.png       # composite grid image
├── metadata.json               # grid structure descriptor
├── {cam_id}_frames/            # full-resolution sampled frames — used for crop export
└── {cam_id}_detections/        # optional, never produced by this app: bounding boxes
                             # from an external detector, named
                             # frame_NNNNNN_x1_y1_x2_y2.jpg
```

### `metadata.json` schema

```json
{
  "drop_id": "DFDF1-10",
  "segment_index": 1,
  "n_columns": 5,
  "n_rows": 25,
  "cell_width": 640,
  "cell_height": 360,
  "left_label_width": 170,
  "top_header_height": 40,
  "cells": [
    {
      "row": 0,
      "col": 0,
      "camera_id": "1",
      "frame_rank": 0,
      "time_seconds": 0,
      "time_label": "0:00",
      "image_id": "1_f000000",
      "image_file": "frame_000000.jpg"
    }
  ]
}
```

This file is produced automatically by the Prepare tab.

---

## Output format

All outputs are written to the segment folder.

| File | Format | Description |
|---|---|---|
| `annotations.csv` | CSV (UTF-8 with BOM) | One row per annotation — all metadata columns |
| `annotations.xlsx` | Excel | Same table; navy header, alternating rows, uncertain rows highlighted in yellow |
| `planche_annotated.png` | PNG | Composite image with coloured annotation circles and species labels |
| `crops/<name>/*.jpg` | JPEG | One crop per annotation, organised by scientific name |

### Annotation table columns

In file order:

`campaign` · `location` · `site` · `latitude` · `longitude` · `drop_id` · `date` · `camera_id` · `frame_rank` · `time_seconds` · `time_label` · `row` · `col` · `image_id` · `image_file` · `x_image` · `y_image` · `x_data` · `y_data` · `x_in_cell` · `y_in_cell` · `species_common_name` · `species_scientific_name` · `family` · `species_color` · `count` · `comment` · `is_uncertain` · `user` · `timestamp` · `habitat` · `visibility` · `depth`

---

## Species management

Go to **File → Manage species** to add, remove, or recolour species.

The species list is stored in `%APPDATA%\FISH Annot\species_config.json`, seeded on first use from the `config/species_config.json` shipped with the app, and shared across all sessions. It is kept outside the installation folder so that reinstalling or updating the app does not discard it. Each entry includes:

| Field | Example |
|---|---|
| Common name | Chirurgien bleu |
| Scientific name | *Acanthurus coeruleus* |
| Family | Acanthuridae |
| Hex colour | `#3182CE` |
| Active flag | `true` / `false` |

The default configuration includes 42 tropical reef fish species (Caribbean context). The file can also be edited directly with any text editor.

---

## Crop export

**File → Export crops by species** extracts one image crop per annotation, organised into sub-folders by scientific name:

```
crops/
├── Acanthurus_coeruleus/
│   ├── 1_t000045_812_390.jpg        # {image_id}_{x1}_{y1}.jpg
│   └── ...
└── Lutjanus_synagris/
    └── ...
```

Crops require the sampled frames, so tick **Save source frames** in the Prepare tab. A detection bounding box is used when one is available, otherwise a 200 x 200 px square centred on the click position.

---

## Project structure

```
fish.annot/
├── main.py                      # entry point + QSS stylesheet
├── requirements.txt
├── LICENSE
├── README.md
├── ui/
│   ├── main_window.py           # main window, tab container
│   ├── annotation_tab.py        # image viewer + annotation logic
│   ├── prepare_tab.py           # board building UI + worker thread
│   └── help_content.py          # in-app user guide
├── core/
│   ├── planche_builder.py       # video/image to composite board + metadata.json
│   ├── click_handler.py         # pixel to grid-cell coordinate mapping
│   ├── exporter.py              # CSV/XLSX export, crop export, annotated image
│   ├── metadata_loader.py       # metadata.json loading and validation
│   └── species_manager.py       # species management dialog
├── config/
│   ├── species_config.json      # species database
│   └── viewer_config.json       # UI state (vertical guide position)
├── assets/
│   └── icon.ico
└── build/
    ├── fish_annot.spec          # PyInstaller build configuration
    └── fish_annot_setup.iss     # Inno Setup installer script
```

---

## Notes

- Tested on Windows 11, Python 3.10, PySide6 6.11
- Building a board holds one segment of frames in memory; reduce **Frames / segment** if you work with many cameras at high resolution

---

## Citation

If you use this software in your research, please cite:

```bibtex
@software{anonymous_2026_fish_annot,
  author    = {Anonymous},
  title     = {{FISH Annot: a Windows tool for building annotation boards
               from underwater videos and annotating fish species}},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.22699643},
  url       = {https://doi.org/10.5281/zenodo.22699643}
}
```

---

## License

[MIT License](LICENSE) — Copyright (c) 2026 Anonymous Authors
