"""ATAR checkpoint system — save/restore file states before destructive ops."""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime


class Checkpoint:
    def __init__(self, path: str = ".atar/checkpoints") -> None:
        self.path = path
        os.makedirs(path, exist_ok=True)

    def save(self, file_path: str) -> str | None:
        """Save a backup of file_path. Returns checkpoint ID or None."""
        if not os.path.exists(file_path):
            return None
        import uuid
        cid = uuid.uuid4().hex[:8]
        dest = os.path.join(self.path, f"{cid}_{os.path.basename(file_path)}")
        shutil.copy2(file_path, dest)
        # Save metadata
        with open(os.path.join(self.path, f"{cid}.meta"), "w") as f:
            f.write(f"original={file_path}\ntime={datetime.now(UTC).isoformat()}\n")
        return cid

    def restore(self, cid: str) -> bool:
        """Restore file from checkpoint. Returns True if successful."""
        meta_file = os.path.join(self.path, f"{cid}.meta")
        if not os.path.exists(meta_file):
            return False
        with open(meta_file) as f:
            meta = dict(line.strip().split("=", 1) for line in f if "=" in line)
        original = meta.get("original", "")
        if not original:
            return False
        # Find the backup file
        for fname in os.listdir(self.path):
            if fname.startswith(cid) and not fname.endswith(".meta"):
                shutil.copy2(os.path.join(self.path, fname), original)
                return True
        return False

    def list(self) -> list[dict]:
        """List all checkpoints."""
        results = []
        for fname in os.listdir(self.path):
            if fname.endswith(".meta"):
                cid = fname.replace(".meta", "")
                with open(os.path.join(self.path, fname)) as f:
                    meta = dict(line.strip().split("=", 1) for line in f if "=" in line)
                results.append({"id": cid, "original": meta.get("original", ""), "time": meta.get("time", "")})
        return results

    def cleanup(self, cid: str) -> None:
        """Remove a checkpoint."""
        for fname in os.listdir(self.path):
            if fname.startswith(cid):
                os.unlink(os.path.join(self.path, fname))
