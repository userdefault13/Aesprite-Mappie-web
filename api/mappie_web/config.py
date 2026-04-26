from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORE_PATH = Path("/Users/juliuswong/Dev/Aseprite-Mappie")
DEFAULT_ARTIFACT_ROOT = APP_ROOT / "artifacts"
DEFAULT_UPLOAD_ROOT = APP_ROOT / "uploads"


def core_path() -> Path:
    return Path(os.getenv("MAPPIE_CORE_PATH", str(DEFAULT_CORE_PATH))).expanduser().resolve()


def artifact_root() -> Path:
    return Path(os.getenv("MAPPIE_ARTIFACT_ROOT", str(DEFAULT_ARTIFACT_ROOT))).expanduser().resolve()


def upload_root() -> Path:
    return Path(os.getenv("MAPPIE_UPLOAD_ROOT", str(DEFAULT_UPLOAD_ROOT))).expanduser().resolve()


def ensure_core_importable() -> Path:
    root = core_path()
    src = root / "src"
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))
    return root


def resolve_aseprite_bin() -> str | None:
    explicit = os.getenv("ASEPRITE_BIN")
    candidates = [
        explicit,
        shutil.which("aseprite"),
        "/Applications/Aseprite.app/Contents/MacOS/aseprite",
        str(Path.home() / "Library/Application Support/Steam/steamapps/common/Aseprite/Aseprite.app/Contents/MacOS/aseprite"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.exists() and path.is_file():
            return str(path)
    return None
