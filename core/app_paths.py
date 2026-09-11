"""Where the application reads and writes its own configuration.

The JSON files shipped in ``config/`` are *defaults*. Once installed they sit next to
the executable, which is the wrong place to write to: the folder may be read-only when
the app is installed for all users, and the next installer run replaces its contents —
taking the species list the annotator had built with it.

Anything the user can edit therefore lives in ``%APPDATA%\\FISH Annot`` and is seeded
from the bundled default the first time it is needed.
"""

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "FISH Annot"


def bundled_config_dir():
    """Read-only defaults — inside the PyInstaller bundle when frozen."""
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = Path(__file__).resolve().parent.parent
    return Path(base) / "config"


def user_config_dir():
    """Writable per-user folder, created on demand."""
    root = os.environ.get("APPDATA") or (Path.home() / ".config")
    path = Path(root) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_file(name):
    """Path of a user-writable config file, seeded from the bundled default.

    Falls back to the bundled file if the per-user copy cannot be created, so a
    locked-down machine still reads a valid configuration instead of crashing.
    """
    default = bundled_config_dir() / name
    try:
        target = user_config_dir() / name
        if not target.exists() and default.exists():
            shutil.copyfile(default, target)
        return target
    except OSError:
        return default
