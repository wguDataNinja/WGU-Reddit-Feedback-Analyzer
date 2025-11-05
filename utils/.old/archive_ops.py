# filename: archive_ops.py

from pathlib import Path
import shutil
from datetime import datetime

def move_to_archive(in_path: Path, archive_dir: Path) -> None:
    """
    Move a processed file to an archive directory.
    """
    archive_dir.mkdir(parents=True, exist_ok=True)
    if in_path.exists():
        dest = archive_dir / in_path.name
        shutil.move(str(in_path), str(dest))
        print(f"[archive] Moved {in_path} → {dest}")

def archive_input(input_path: Path, archive_dir: Path) -> None:
    """
    Copy and timestamp-archive a file (for reproducibility).
    """
    archive_dir.mkdir(parents=True, exist_ok=True)
    if input_path.exists():
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        dest = archive_dir / f"{input_path.stem}_{timestamp}.jsonl"
        shutil.copy(str(input_path), str(dest))
        print(f"[archive] Copied {input_path} → {dest}")
