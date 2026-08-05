"""ATAR Ink launcher — auto-install deps, start server, launch Ink UI."""

from __future__ import annotations

import subprocess
import sys
import threading
import time


def launch(ink_dir: str, port: int = 8420) -> None:
    """Launch ATAR Ink with auto-setup and server management."""

    # 1. Install npm deps if fresh (show live output)
    import os
    if not os.path.isdir(os.path.join(ink_dir, "node_modules")):
        print("Installing Node.js dependencies...")
        subprocess.run(["npm", "install"], cwd=ink_dir, check=True)

    # 2. Install fastapi if missing (show live output)
    try:
        import fastapi  # noqa: F401
    except ImportError:
        print("Installing Python API dependencies...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "fastapi", "uvicorn"],
            check=True,
        )

    # 3. Start API server in background
    from atar_cli.api_server import start_server
    server_thread = threading.Thread(target=start_server, args=("127.0.0.1", port), daemon=True)
    server_thread.start()

    # 4. Wait for server to boot
    import urllib.request
    for _ in range(15):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.3)
    else:
        print("Server may still be starting...")

    # 5. Launch Ink UI
    subprocess.run(["npx", "tsx", "src/cli.tsx"], cwd=ink_dir)
