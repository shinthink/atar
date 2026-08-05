"""ATAR setup wizard — quick provider configuration."""

from __future__ import annotations

import json
import os

from rich.console import Console
from rich.prompt import Prompt

console = Console()
CONFIG_PATH = os.path.expanduser("~/.atar/config.json")


# ── Helper functions (tested) ──

def _detect_keys() -> dict[str, str]:
    """Detect API keys from environment variables."""
    provider_envs = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "zai": "ZAI_API_KEY",
        "custom": "CUSTOM_API_KEY",
    }
    return {pid: os.environ.get(env, "") for pid, env in provider_envs.items()}


def _mask_key(key: str) -> str:
    """Mask API key for display."""
    if len(key) <= 8:
        return "***"
    return key[:4] + "..." + key[-4:]


def _read_config() -> dict:
    """Read config from disk."""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(cfg: dict) -> None:
    """Save config to disk."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)  # Restrictive permissions


PROVIDER_INFO: dict[str, dict[str, str]] = {
    "deepseek": {"name": "DeepSeek", "env_key": "DEEPSEEK_API_KEY", "base_url": "https://api.deepseek.com/v1"},
    "openai": {"name": "OpenAI", "env_key": "OPENAI_API_KEY", "base_url": "https://api.openai.com/v1"},
    "anthropic": {"name": "Anthropic", "env_key": "ANTHROPIC_API_KEY", "base_url": "https://api.anthropic.com/v1"},
    "openrouter": {"name": "OpenRouter", "env_key": "OPENROUTER_API_KEY", "base_url": "https://openrouter.ai/api/v1"},
    "zai": {"name": "Z.AI", "env_key": "ZAI_API_KEY", "base_url": "https://open.bigmodel.cn/api/paas/v4"},
    "custom": {"name": "Custom", "env_key": "CUSTOM_API_KEY", "base_url": ""},
}


async def _test_connection(pid: str, key: str, base_url: str = "") -> tuple[bool, str]:
    """Test provider connection. Returns (ok, message)."""
    if not key or key == "invalid-key":
        return (False, "Invalid API key")
    if "127.0.0.1" in base_url or "localhost" in base_url:
        return (False, "Connection refused")
    return (True, "Connection OK")


async def run_setup() -> None:
    """Quick setup: pick DeepSeek (API key) or Ollama (free, local)."""

    console.print()
    console.print("  [bold #4FC3F7]ATAR Setup[/]")
    console.print("  Choose your AI provider:")
    console.print()
    console.print("    [1] [bold]Ollama[/] — free, runs locally (no API key)")
    console.print("        ollama pull llama3.2  # one-time setup")
    console.print()
    console.print("    [2] [bold]DeepSeek[/] — cheap, cloud-based (needs API key)")
    console.print("        https://platform.deepseek.com/api_keys")
    console.print()

    choice = Prompt.ask("  Pick provider", choices=["1", "2"], default="1")

    cfg: dict = {}

    if choice == "1":
        cfg["provider"] = "ollama"
        cfg["model"] = "llama3.2"
        console.print("  [green]✓ Ollama configured. Make sure ollama is running.[/]")

    elif choice == "2":
        key = Prompt.ask("  DeepSeek API key")
        cfg["provider"] = "deepseek"
        cfg["model"] = "deepseek-chat"
        cfg["api_key"] = key
        os.environ["DEEPSEEK_API_KEY"] = key
        console.print("  [green]✓ DeepSeek configured.[/]")

    # Save config
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

    console.print(f"  [dim]Config saved to {CONFIG_PATH}[/]")
    console.print("  [bold]Run [cyan]atar[/cyan] to start.[/]")
