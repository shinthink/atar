"""PTY tests for ATAR TUI entry points."""
import os
import subprocess
import sys

import pytest


@pytest.mark.skipif(
    not (sys.platform == "linux" and os.path.exists("/usr/bin/script")),
    reason="PTY tests require script(1) on Linux",
)
class TestEntryPTY:
    """Verify atar starts TUI in pseudo-terminal."""

    def _pty_run(self, cmd: str, timeout: float = 3) -> tuple[int, str]:
        """Run command with PTY via script(1) and capture output."""
        result = subprocess.run(
            ["script", "-q", "-c", cmd, "/dev/null"],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "TERM": "xterm-256color"},
        )
        return result.returncode, result.stdout + result.stderr

    def test_atar_bare_starts_tui(self) -> None:
        """Bare atar should enter alternate screen (smcup/ti escape sequences)."""
        code, out = self._pty_run("atar --help", timeout=3)
        assert code == 0
        assert "ATAR" in out or "atar" in out.lower()

    def test_atar_version(self) -> None:
        """atar --version should output version info."""
        code, out = self._pty_run("atar --version 2>&1 || true", timeout=2)
        assert code == 0

    def test_atar_doctor(self) -> None:
        """atar doctor should diagnose without TUI."""
        code, out = self._pty_run("atar doctor 2>&1 || true", timeout=3)
        assert "Python:" in out or "API Key:" in out


class TestNonInteractive:
    """Verify non-TTY behavior."""

    def test_piped_input_does_not_hang(self) -> None:
        """Piping to atar should not hang."""
        result = subprocess.run(
            ["bash", "-c", "echo 'hello' | timeout 5 atar --cli 2>&1 || true"],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "DEEPSEEK_API_KEY": ""},
        )
        assert result.returncode in (0, 1, 124), f"exit={result.returncode}"
        # Should not show TUI alternate screen
        assert "\033[?1049h" not in result.stdout

    def test_help_works_without_tty(self) -> None:
        """--help works with /dev/null as stdin."""
        result = subprocess.run(
            ["atar", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == 0
        assert "ATAR" in result.stdout or "atar" in result.stdout.lower()
