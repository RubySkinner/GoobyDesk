#!/usr/bin/env python3
"""Backup helpers for JSON storage files."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil


def create_json_backup(path: str | Path, backup_dir: str | Path | None = None) -> Path:
    """Create a timestamped backup copy of a JSON file.

    Args:
        path: Source JSON file path.
        backup_dir: Optional destination directory.

    Returns:
        Path to the created backup file.

    Raises:
        FileNotFoundError: If source path does not exist.
    """
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Cannot backup missing file: {source}")

    target_dir = Path(backup_dir) if backup_dir else source.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_name = f"{source.stem}.{timestamp}.bak{source.suffix}"
    backup_path = target_dir / backup_name

    shutil.copy2(source, backup_path)
    return backup_path
