"""ATAR Docker sandbox — isolated command execution with automatic setup and cleanup.

Uses docker CLI (not SDK) for zero-dependency operation.
Auto-detects Docker availability. Falls back to local when unavailable.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field


@dataclass
class DockerSandbox:
    """Lightweight Docker sandbox for isolated command execution."""

    image: str = "alpine:3.20"
    container_name: str = f"atar-sandbox-{os.getpid()}"
    workspace_mount: str = ""
    memory_limit: str = "512m"
    cpu_limit: str = "1.0"
    network_mode: str = "bridge"  # "none" for fully isolated
    timeout: int = 300

    _ready: bool = field(default=False, init=False)
    _docker_available: bool | None = field(default=None, init=False)

    @property
    def name(self) -> str:
        return "docker"

    async def is_available(self) -> bool:
        """Check if Docker is available and working."""
        if self._docker_available is not None:
            return self._docker_available
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "version", "--format", "{{.Server.Version}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            self._docker_available = proc.returncode == 0
            return self._docker_available
        except Exception:
            self._docker_available = False
            return False

    async def setup(self) -> bool:
        """Ensure sandbox container is running."""
        if self._ready:
            return True

        if not await self.is_available():
            return False

        ws = self.workspace_mount or os.getcwd()

        try:
            # Check if container already exists
            proc = await asyncio.create_subprocess_exec(
                "docker", "ps", "-a", "--filter", f"name={self.container_name}",
                "--format", "{{.Names}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)

            if self.container_name in stdout.decode().strip():
                # Container exists — start it if stopped
                proc = await asyncio.create_subprocess_exec(
                    "docker", "start", self.container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(proc.communicate(), timeout=10)
            else:
                # Create new container
                cmd = [
                    "docker", "run", "-d",
                    "--name", self.container_name,
                    "--rm",
                    "--memory", self.memory_limit,
                    "--cpus", self.cpu_limit,
                    "--network", self.network_mode,
                    "-v", f"{ws}:/workspace",
                    "-w", "/workspace",
                    self.image,
                    "sleep", "infinity",
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                if proc.returncode != 0:
                    # Image might not exist — pull it
                    pull_proc = await asyncio.create_subprocess_exec(
                        "docker", "pull", self.image,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await asyncio.wait_for(pull_proc.communicate(), timeout=60)
                    # Retry container creation
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                    if proc.returncode != 0:
                        return False

            self._ready = True
            return True

        except Exception:
            return False

    async def run(self, command: str, cwd: str = "/workspace", timeout: int | None = None) -> tuple[int, str, str]:
        """Execute a command inside the sandbox. Returns (exit_code, stdout, stderr)."""
        if not self._ready and not await self.setup():
            return -1, "", "Docker sandbox not available"

        t = timeout or self.timeout
        safe_cmd = command.replace("'", "'\"'\"'")
        # Ensure cwd is absolute — Docker exec requires it
        # Translate host path to container path (workspace is mounted at /workspace)
        host_cwd = os.path.abspath(cwd) if cwd else "/workspace"
        ws = self.workspace_mount or os.getcwd()
        if host_cwd.startswith(ws):
            rel = os.path.relpath(host_cwd, ws)
            container_cwd = "/workspace" if rel == "." else f"/workspace/{rel}"
        else:
            container_cwd = "/workspace"

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "exec", "-w", container_cwd,
                self.container_name,
                "sh", "-c", safe_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=t)
            return (
                proc.returncode or 0,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )
        except TimeoutError:
            # Kill the docker exec
            try:
                kill_proc = await asyncio.create_subprocess_exec(
                    "docker", "stop", self.container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await kill_proc.communicate()
            except Exception:
                pass
            return -1, "", f"Command timed out after {t}s — container killed"
        except Exception as e:
            return -1, "", str(e)

    async def cleanup(self) -> None:
        """Stop and remove the sandbox container."""
        if not self._ready:
            return
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "stop", "-t", "5", self.container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10)
        except Exception:
            pass
        self._ready = False

    async def __aenter__(self):
        await self.setup()
        return self

    async def __aexit__(self, *args):
        await self.cleanup()


# Global sandbox instance
_sandbox: DockerSandbox | None = None


async def get_sandbox() -> DockerSandbox:
    """Get or create the global Docker sandbox."""
    global _sandbox
    if _sandbox is None:
        _sandbox = DockerSandbox()
    if not _sandbox._ready:
        await _sandbox.setup()
    return _sandbox


async def run_sandboxed(command: str, cwd: str = "/workspace", timeout: int = 60) -> tuple[bool, str, str]:
    """Run a command in Docker sandbox with automatic fallback to local.

    Returns (success, output, error).
    """
    try:
        sb = await get_sandbox()
        if sb._ready:
            exit_code, stdout, stderr = await sb.run(command, cwd, timeout)
            if exit_code == -1 and "not available" in stderr:
                # Fallback to local
                import subprocess as sp
                result = sp.run(command, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd)
                return result.returncode == 0, result.stdout, result.stderr
            return exit_code == 0, stdout, stderr
        else:
            # Docker not available — use local directly
            import subprocess as sp
            result = sp.run(command, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd)
            return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


async def cleanup_sandbox() -> None:
    """Clean up the global sandbox."""
    global _sandbox
    if _sandbox:
        await _sandbox.cleanup()
        _sandbox = None
