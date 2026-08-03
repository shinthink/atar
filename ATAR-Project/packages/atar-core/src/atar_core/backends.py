"""ATAR execution backends — Docker, SSH, and local."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod


# ── Abstract backend ──
class ExecutionBackend(ABC):
    """Abstract backend for running commands outside the local shell."""
    name: str = "local"

    @abstractmethod
    def run(self, command: str, workdir: str = "", timeout: int = 30) -> tuple[int, str, str]:
        """Run command. Returns (exit_code, stdout, stderr)."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is usable."""
        ...


class LocalBackend(ExecutionBackend):
    name = "local"

    def run(self, command: str, workdir: str = "", timeout: int = 30) -> tuple[int, str, str]:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                cwd=workdir or None, timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as e:
            return -1, e.stdout or "", f"Timeout after {timeout}s"
        except Exception as e:
            return -1, "", str(e)

    def is_available(self) -> bool:
        return True


class DockerBackend(ExecutionBackend):
    name = "docker"

    def __init__(self, image: str = "python:3.12-slim", network: str = "none") -> None:
        self.image = image
        self.network = network

    def run(self, command: str, workdir: str = "", timeout: int = 30) -> tuple[int, str, str]:
        try:
            result = subprocess.run(
                ["docker", "run", "--rm", f"--network={self.network}",
                 "--memory=512m", "--cpus=1",
                 "-w", workdir or "/tmp",
                 self.image, "sh", "-c", command],
                capture_output=True, text=True, timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Docker timeout after {timeout}s"
        except FileNotFoundError:
            return -1, "", "Docker not installed"
        except Exception as e:
            return -1, "", str(e)

    def is_available(self) -> bool:
        try:
            subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False


class SSHBackend(ExecutionBackend):
    name = "ssh"

    def __init__(self, host: str, user: str = "root", port: int = 22, key_path: str = "") -> None:
        self.host = host
        self.user = user
        self.port = port
        self.key_path = key_path

    def run(self, command: str, workdir: str = "", timeout: int = 30) -> tuple[int, str, str]:
        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no",
                   "-o", "ConnectTimeout=10",
                   "-p", str(self.port)]
        if self.key_path:
            ssh_cmd.extend(["-i", self.key_path])
        ssh_cmd.append(f"{self.user}@{self.host}")
        if workdir:
            ssh_cmd.append(f"cd {workdir} && {command}")
        else:
            ssh_cmd.append(command)
        try:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"SSH timeout after {timeout}s"
        except Exception as e:
            return -1, "", str(e)

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
                 f"{self.user}@{self.host}", "echo ok"],
                capture_output=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False


# ── Backend registry ──
_backend: ExecutionBackend = LocalBackend()


def get_backend() -> ExecutionBackend:
    return _backend


def set_backend(backend: ExecutionBackend) -> None:
    global _backend
    _backend = backend


def switch_backend(name: str, config: dict | None = None) -> ExecutionBackend:
    """Switch to named backend. Config keys passed to backend constructor."""
    config = config or {}
    if name == "local":
        b = LocalBackend()
    elif name == "docker":
        b = DockerBackend(
            image=config.get("docker_image", "python:3.12-slim"),
            network=config.get("docker_network", "none"),
        )
    elif name == "ssh":
        b = SSHBackend(
            host=config.get("ssh_host", ""),
            user=config.get("ssh_user", "root"),
            port=int(config.get("ssh_port", 22)),
            key_path=config.get("ssh_key", ""),
        )
    else:
        raise ValueError(f"Unknown backend: {name}")
    set_backend(b)
    return b
