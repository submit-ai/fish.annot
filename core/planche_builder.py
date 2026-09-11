import json
import math
import shutil
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont

LEFT_LABEL_WIDTH = 120
TOP_HEADER_HEIGHT = 35


def _font(size=10):
    for name in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _fmt_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def _make_planche(cells, n_rows, n_cols, col_headers, row_labels, cell_w, cell_h):
    """
    cells : dict {(row, col): PIL.Image | None}
    Returns : PIL.Image
    """
    total_w = LEFT_LABEL_WIDTH + n_cols * cell_w
    total_h = TOP_HEADER_HEIGHT + n_rows * cell_h

    img = Image.new("RGB", (total_w, total_h), (40, 40, 40))
    draw = ImageDraw.Draw(img)
    font = _font(10)

    draw.rectangle([0, 0, total_w, TOP_HEADER_HEIGHT - 1], fill=(25, 25, 25))
    draw.rectangle([0, 0, LEFT_LABEL_WIDTH - 1, total_h], fill=(25, 25, 25))

    for col, header in enumerate(col_headers):
        cx = LEFT_LABEL_WIDTH + col * cell_w + cell_w // 2
        draw.text((cx, TOP_HEADER_HEIGHT // 2), str(header)[:24],
                  fill=(200, 200, 200), font=font, anchor="mm")

    for row, label in enumerate(row_labels):
        cy = TOP_HEADER_HEIGHT + row * cell_h + cell_h // 2
        draw.text((LEFT_LABEL_WIDTH // 2, cy), str(label),
                  fill=(200, 200, 200), font=font, anchor="mm")

    for (row, col), thumb in cells.items():
        x = LEFT_LABEL_WIDTH + col * cell_w
        y = TOP_HEADER_HEIGHT + row * cell_h
        if thumb is not None:
            resized = thumb.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
            img.paste(resized, (x, y))
        else:
            draw.rectangle([x + 1, y + 1, x + cell_w - 2, y + cell_h - 2], fill=(15, 15, 15))

    # grid lines
    for c in range(n_cols + 1):
        x = LEFT_LABEL_WIDTH + c * cell_w
        draw.line([(x, 0), (x, total_h)], fill=(60, 60, 60))
    for r in range(n_rows + 1):
        y = TOP_HEADER_HEIGHT + r * cell_h
        draw.line([(0, y), (total_w, y)], fill=(60, 60, 60))

    return img


def build_from_videos(video_paths, params, output_dir, drop_id,
                      on_progress=None, on_log=None, check_abort=None):
    """
    video_paths      : list[Path | str]
    params           : {
        start_delay       : int   (s, default 0)
        frame_interval    : float (s, default 1.0)
        frames_per_seg    : int   (default 100)
        cell_width        : int   (default 640)
        cell_height       : int   (default 360)
        save_frames       : bool  (default False)
    }
    output_dir       : Path | str
    drop_id          : str
    on_progress(pct) : callback 0-100
    on_log(msg)      : callback str
    check_abort()    : returns True to stop
    Returns (n_segments, drop_dir_str)
    """
    cell_w       = params.get("cell_width",       640)
    cell_h       = params.get("cell_height",      360)
    start_delay  = params.get("start_delay",      0)
    interval     = max(0.1, params.get("frame_interval", 1.0))
    fps_seg      = params.get("frames_per_seg",   100)
    save_frames  = params.get("save_frames",      False)

    n_cols   = len(video_paths)
    drop_dir = Path(output_dir) / drop_id

    def log(msg):
        if on_log:
            on_log(msg)

    def progress(pct):
        if on_progress:
            on_progress(int(pct))

    def aborted():
        return check_abort and check_abort()

    log(f"Ouverture de {n_cols} vidéo(s)…")

    caps, fps_list = [], []
    for vp in video_paths:
        cap = cv2.VideoCapture(str(vp))
        if not cap.isOpened():
            raise RuntimeError(f"Impossible d'ouvrir la vidéo : {vp}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        caps.append(cap)
        fps_list.append(fps)

    # seek to start_delay
    for cap, fps in zip(caps, fps_list):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_delay * fps))

    col_headers = [Path(vp).stem[:24] for vp in video_paths]

    # estimate total frames for progress
    total_est = max(
        (cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps / interval - start_delay / interval)
        for cap, fps in zip(caps, fps_list)
    ) if caps else 1.0
    total_est = max(1.0, total_est)

    # per-camera global frame ranks (continuous across segments)
    cam_ranks = [0] * n_cols
    exhausted = [False] * n_cols
    seg_idx = 0
    frames_done = 0

    while not all(exhausted):
        if aborted():
            break

        seg_idx += 1
        seg_dir = drop_dir / f"seg_{seg_idx:03d}"
        seg_dir.mkdir(parents=True, exist_ok=True)

        if save_frames:
            for col in range(n_cols):
                (seg_dir / f"{col + 1}_frames").mkdir(exist_ok=True)

        cells      = {}
        row_labels = []
        cells_meta = []
        actual_rows = 0

        for row in range(fps_seg):
            if aborted():
                break

            row_label = None
            any_frame = False

            for col, (cap, fps, vp) in enumerate(zip(caps, fps_list, video_paths)):
                if exhausted[col]:
                    cells[(row, col)] = None
                    continue

                ret, bgr = cap.read()
                if not ret:
                    exhausted[col] = True
                    cells[(row, col)] = None
                    continue

                any_frame = True
                pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                time_s = pos_ms / 1000.0
                time_lbl = _fmt_time(time_s)

                if row_label is None:
                    row_label = time_lbl

                frame_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                # Downscale immediately: a whole segment is held in memory at once,
                # and full-resolution frames would cost frames_per_seg * n_cols *
                # ~6 MB (over 3 GB for 100 rows x 3 cameras at 1080p). _make_planche
                # resizes to the same size with the same filter, so the board is
                # unchanged.
                thumb = Image.fromarray(frame_rgb).resize(
                    (cell_w, cell_h), Image.Resampling.LANCZOS
                )
                cells[(row, col)] = thumb

                cam_id   = str(col + 1)
                rank     = cam_ranks[col]
                img_file = f"frame_{rank:06d}.jpg"
                # Keyed on the frame rank, not on the timestamp: two frames of the
                # same camera fall in the same second as soon as the interval drops
                # below 1 s, and a duplicated image_id makes the exported rows
                # ambiguous.
                img_id   = f"{cam_id}_f{rank:06d}"

                if save_frames:
                    # Saved at source resolution on purpose. Crop export cuts into
                    # these files, so a board-sized thumbnail would make every crop
                    # useless. The image is written and released frame by frame, so
                    # peak memory stays at one frame — the reason the board cells are
                    # downscaled above still holds.
                    Image.fromarray(frame_rgb).save(
                        seg_dir / f"{cam_id}_frames" / img_file, "JPEG", quality=90
                    )

                cells_meta.append({
                    "row": row, "col": col,
                    "camera_id": cam_id,
                    "frame_rank": rank,
                    "time_seconds": int(time_s),
                    "time_label": time_lbl,
                    "image_id": img_id,
                    "image_file": img_file,
                })
                cam_ranks[col] += 1

                # skip to next interval using grab (faster than seek for H.264)
                to_skip = max(0, round(interval * fps) - 1)
                for _ in range(to_skip):
                    if not cap.grab():
                        exhausted[col] = True
                        break

            row_labels.append(row_label or "")
            if any_frame:
                actual_rows = row + 1
                frames_done += 1
            else:
                break

        if actual_rows == 0:
            # rmdir() would raise here as soon as "save source frames" is on: the
            # {cam}_frames/ subfolders were created when the segment opened, so the
            # directory is not empty even though no frame was read.
            shutil.rmtree(seg_dir, ignore_errors=True)
            seg_idx -= 1
            break

        planche = _make_planche(
            cells, actual_rows, n_cols,
            col_headers, row_labels[:actual_rows],
            cell_w, cell_h
        )
        planche.save(seg_dir / "planche_verticale.png", "PNG")

        metadata = {
            "drop_id": drop_id,
            "segment_index": seg_idx,
            "n_columns": n_cols,
            "n_rows": actual_rows,
            "cell_width": cell_w,
            "cell_height": cell_h,
            "left_label_width": LEFT_LABEL_WIDTH,
            "top_header_height": TOP_HEADER_HEIGHT,
            "cells": cells_meta,
        }
        with open(seg_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        progress(min(99, frames_done / total_est * 100))
        log(f"  seg_{seg_idx:03d} — {actual_rows} ligne(s)")

    for cap in caps:
        cap.release()

    progress(100)
    log(f"Terminé : {seg_idx} segment(s) → {drop_dir}")
    return seg_idx, str(drop_dir)


def build_from_images(image_paths, params, output_dir, drop_id,
                      on_progress=None, on_log=None, check_abort=None):
    """
    image_paths : list[Path | str]
    params      : {
        n_columns         : int   (default 5)
        images_per_seg    : int   (default 20)  → rows per segment
        cell_width        : int   (default 640)
        cell_height       : int   (default 360)
    }
    """
    n_cols      = params.get("n_columns",      5)
    imgs_per_seg = params.get("images_per_seg", 20)
    cell_w      = params.get("cell_width",     640)
    cell_h      = params.get("cell_height",    360)

    drop_dir = Path(output_dir) / drop_id
    total    = len(image_paths)

    def log(msg):
        if on_log:
            on_log(msg)

    def progress(pct):
        if on_progress:
            on_progress(int(pct))

    def aborted():
        return check_abort and check_abort()

    log(f"{total} image(s) — {n_cols} colonne(s), {imgs_per_seg} ligne(s)/segment")

    n_rows_per_seg = imgs_per_seg
    imgs_per_segment = n_cols * n_rows_per_seg
    n_segs = math.ceil(total / imgs_per_segment) if total else 0

    col_headers = [str(c + 1) for c in range(n_cols)]

    for seg_idx in range(1, n_segs + 1):
        if aborted():
            break

        start = (seg_idx - 1) * imgs_per_segment
        batch = image_paths[start: start + imgs_per_segment]

        n_rows = math.ceil(len(batch) / n_cols)
        seg_dir = drop_dir / f"seg_{seg_idx:03d}"
        seg_dir.mkdir(parents=True, exist_ok=True)

        cells      = {}
        row_labels = []
        cells_meta = []

        for idx, img_path in enumerate(batch):
            row = idx // n_cols
            col = idx % n_cols

            try:
                # Downscale on load, for the same memory reason as in
                # build_from_videos above.
                thumb = Image.open(img_path).convert("RGB").resize(
                    (cell_w, cell_h), Image.Resampling.LANCZOS
                )
            except Exception as e:
                log(f"  Erreur image {img_path.name}: {e}")
                thumb = Image.new("RGB", (cell_w, cell_h), (30, 30, 30))

            cells[(row, col)] = thumb

            img_path = Path(img_path)
            img_id = f"img_{start + idx:06d}"

            cells_meta.append({
                "row": row, "col": col,
                "camera_id": str(col + 1),
                "frame_rank": start + idx,
                "time_seconds": 0,
                "time_label": img_path.name[:16],
                "image_id": img_id,
                "image_file": img_path.name,
            })

            if col == 0:
                row_labels.append(img_path.stem[:16])

        # fill missing cells in last row
        for col in range(len(batch) % n_cols or n_cols, n_cols):
            row = n_rows - 1
            cells[(row, col)] = None

        planche = _make_planche(
            cells, n_rows, n_cols,
            col_headers, row_labels,
            cell_w, cell_h
        )
        planche.save(seg_dir / "planche_verticale.png", "PNG")

        metadata = {
            "drop_id": drop_id,
            "segment_index": seg_idx,
            "n_columns": n_cols,
            "n_rows": n_rows,
            "cell_width": cell_w,
            "cell_height": cell_h,
            "left_label_width": LEFT_LABEL_WIDTH,
            "top_header_height": TOP_HEADER_HEIGHT,
            "cells": cells_meta,
        }
        with open(seg_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        progress(seg_idx / n_segs * 100)
        log(f"  seg_{seg_idx:03d} — {len(batch)} image(s)")

    progress(100)
    log(f"Terminé : {n_segs} segment(s) → {drop_dir}")
    return n_segs, str(drop_dir)
