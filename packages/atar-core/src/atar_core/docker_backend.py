"""ATAR Docker backend — rootless container execution via docker CLI."""

from __future__ import annotations

import asyncio
import os

from atar_core.backends import Backend, ExecResult


class DockerBackend(Backend):
    """Execute commands in rootless Docker containers."""

    def __init__(self, image: str = "python:3.12-slim", container_name: str = "atar-sandbox") -> None:
        self.image = image
        self.container_name = container_name
        self._ready = False

    @property
    def name(self) -> str:
        return "docker"

    async def _ensure_container(self) -> bool:
        if self._ready:
            return True
        # Check if docker is available
        r = await self._docker("version", timeout=5)
        if r.exit_code != 0:
            return False
        # Check if container exists
        r = await self._docker(f"ps -a --filter name={self.container_name} --format '{{{{.Names}}}}'")
        if self.container_name not in r.stdout:
            # Create container
            cwd = os.getcwd()
            r = await self._docker(
                f"run -d --name {self.container_name} --rm "
                f"-v {cwd}:/workspace -w /workspace "
                f"{self.image} sleep infinity", timeout=30
            )
            if r.exit_code != 0:
                return False
        else:
            # Start if stopped
            r = await self._docker(f"start {self.container_name}")
        self._ready = True
        return True

    async def run(self, command: str, cwd: str = ".", timeout: float = 30) -> ExecResult:
        if not await self._ensure_container():
            # Fallback to local
            from atar_core.backends import LocalBackend
            return await LocalBackend().run(command, cwd, timeout)

        safe_cmd = command.replace("'", "'\\''")
        return await self._docker(
            f"exec {self.container_name} sh -c '{safe_cmd}'", timeout=timeout
        )

    async def cleanup(self) -> None:
        await self._docker(f"stop {self.container_name}", timeout=10)
        self._ready = False

    async def _docker(self, args: str, timeout: float = 30) -> ExecResult:
        proc = await asyncio.create_subprocess_shell(
            f"docker {args}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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
