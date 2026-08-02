"""ATAR execution backends — Section 22.

Local: direct process execution (default).
Docker: rootless container (stub — requires Docker daemon).
SSH: remote execution (stub — requires SSH host).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExecResult:
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""


class Backend:
    """Abstract execution backend. Implementations handle sandboxing."""

    async def run(self, command: str, cwd: str = ".", timeout: float = 30) -> ExecResult:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError


class LocalBackend(Backend):
    """Direct local process execution."""

    @property
    def name(self) -> str:
        return "local"

    async def run(self, command: str, cwd: str = ".", timeout: float = 30) -> ExecResult:
        import asyncio
        proc = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            return ExecResult(exit_code=-1, stderr=f"Timeout after {timeout}s")
        return ExecResult(
            exit_code=proc.returncode or 0,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
        )


class DockerBackend(Backend):
    """Rootless Docker container — requires docker CLI."""

    @property
    def name(self) -> str:
        return "docker"

    async def run(self, command: str, cwd: str = ".", timeout: float = 30) -> ExecResult:
        return ExecResult(exit_code=-1, stderr="Docker backend not yet implemented. Use 'local'.")


class SSHBackend(Backend):
    """Remote SSH execution — requires SSH host config."""

    @property
    def name(self) -> str:
        return "ssh"

    async def run(self, command: str, cwd: str = ".", timeout: float = 30) -> ExecResult:
        return ExecResult(exit_code=-1, stderr="SSH backend not yet implemented. Use 'local'.")


def get_backend(name: str = "local") -> Backend:
    backends = {
        "local": LocalBackend(),
        "docker": DockerBackend(),
        "ssh": SSHBackend(),
    }
    return backends.get(name, LocalBackend())
