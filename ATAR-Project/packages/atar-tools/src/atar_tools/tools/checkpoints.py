"""ATAR checkpoints — pre-mutation file snapshots with list/restore."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from atar_core.paths import atar_data_dir, ensure_dirs

MAX_SNAPSHOTS = 50


def _checkpoint_dir(profile: str = "default") -> Path:
    return atar_data_dir(profile) / "checkpoints"


def checkpoint_before_write(filepath: str, profile: str = "default") -> str | None:
    """Snapshot file before mutation. Returns checkpoint ID or None."""
    if not os.path.isfile(filepath):
        return None
    try:
        ensure_dirs(profile)
        cdir = _checkpoint_dir(profile)
        cdir.mkdir(parents=True, exist_ok=True)
        cid = f"{int(time.time())}_{os.path.basename(filepath)}_{hash(filepath) & 0xFFFF:04x}"
        dest = cdir / cid
        shutil.copy2(filepath, dest)

        # Save metadata
        meta = {
            "id": cid,
            "original": os.path.abspath(filepath),
            "size": os.path.getsize(filepath),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with open(dest.with_suffix(".meta.json"), "w") as f:
            json.dump(meta, f)

        # Prune old snapshots
        _prune(cdir)
        return cid
    except (OSError, PermissionError):
        return None


def list_checkpoints(profile: str = "default") -> list[dict[str, Any]]:
    """List all checkpoints."""
    cdir = _checkpoint_dir(profile)
    if not cdir.exists():
        return []
    result = []
    for meta_file in sorted(cdir.glob("*.meta.json"), reverse=True):
        try:
            with open(meta_file) as f:
                result.append(json.load(f))
        except json.JSONDecodeError:
            pass
    return result[:20]


def restore_checkpoint(checkpoint_id: str, profile: str = "default") -> bool:
    """Restore a file from checkpoint. Returns True on success."""
    cdir = _checkpoint_dir(profile)
    snapshot = cdir / checkpoint_id
    meta_file = snapshot.with_suffix(".meta.json")

    if not snapshot.exists() or not meta_file.exists():
        return False

    try:
        with open(meta_file) as f:
            meta = json.load(f)
        original = meta["original"]
        os.makedirs(os.path.dirname(original), exist_ok=True)
        shutil.copy2(snapshot, original)
        return True
    except (OSError, PermissionError, KeyError):
        return False


def clear_checkpoints(profile: str = "default") -> int:
    """Delete all checkpoints. Returns count removed."""
    cdir = _checkpoint_dir(profile)
    if not cdir.exists():
        return 0
    count = len(list(cdir.glob("*")))
    shutil.rmtree(cdir)
    return count


def _prune(cdir: Path) -> None:
    """Keep only the most recent N snapshots."""
    snapshots = sorted(cdir.glob("*"), key=os.path.getmtime)
    while len(snapshots) > MAX_SNAPSHOTS:
        s = snapshots.pop(0)
        s.unlink(missing_ok=True)
        s.with_suffix(".meta.json").unlink(missing_ok=True)
