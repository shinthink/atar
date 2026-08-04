"""ATAR checkpoint manager — file snapshots before destructive operations."""

from __future__ import annotations

import dataclasses
import os
import time
from collections import deque
from typing import Optional

MAX_CHECKPOINTS = 50


@dataclasses.dataclass
class Checkpoint:
    turn: int
    timestamp: float
    tool: str
    file_path: str
    content: str  # pre-change file content


class CheckpointManager:
    def __init__(self) -> None:
        self._checkpoints: deque[Checkpoint] = deque(maxlen=MAX_CHECKPOINTS)

    def save(self, turn: int, tool: str, file_path: str) -> bool:
        """Save current file content as checkpoint. Returns True if file existed."""
        try:
            with open(file_path) as f:
                content = f.read()
            cp = Checkpoint(turn=turn, timestamp=time.time(), tool=tool,
                           file_path=file_path, content=content)
            self._checkpoints.append(cp)
            return True
        except FileNotFoundError:
            return False  # new file, no checkpoint needed
        except Exception:
            return False

    def undo(self, n: int = 1) -> list[str]:
        """Undo last n checkpoints. Returns list of restored file paths."""
        restored = []
        for _ in range(min(n, len(self._checkpoints))):
            cp = self._checkpoints.pop()
            try:
                os.makedirs(os.path.dirname(cp.file_path) or ".", exist_ok=True)
                with open(cp.file_path, "w") as f:
                    f.write(cp.content)
                restored.append(cp.file_path)
            except Exception:
                pass
        return restored

    def list_checkpoints(self) -> list[dict]:
        """List recent checkpoints."""
        return [
            {"turn": cp.turn, "tool": cp.tool, "file": cp.file_path,
             "time": time.strftime("%H:%M:%S", time.localtime(cp.timestamp))}
            for cp in self._checkpoints
        ]

    def count(self) -> int:
        return len(self._checkpoints)


# Global per-session manager
_checkpoint_mgr: CheckpointManager | None = None


def get_checkpoints() -> CheckpointManager:
    global _checkpoint_mgr
    if _checkpoint_mgr is None:
        _checkpoint_mgr = CheckpointManager()
    return _checkpoint_mgr


def reset_checkpoints() -> None:
    global _checkpoint_mgr
    _checkpoint_mgr = CheckpointManager()
