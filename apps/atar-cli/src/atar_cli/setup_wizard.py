"""ATAR first-run setup wizard — interactive provider configuration."""

from __future__ import annotations

import json
import os
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()

CONFIG_PATH = os.path.expanduser("~/.atar/config.json")

PROVIDER_INFO: dict[str, dict[str, str]] = {
    "deepseek": {
        "name": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "description": "Best value. Native tool calling via OpenAI-compatible API.",
        "signup": "https://platform.deepseek.com/api_keys",
    },
    "openai": {
        "name": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "description": "GPT-5.6, GPT-4o. Most capable, highest cost.",
        "signup": "https://platform.openai.com/api-keys",
    },
    "anthropic": {
        "name": "Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com/v1",
        "description": "Claude Sonnet 4. Excellent for coding and analysis.",
        "signup": "https://console.anthropic.com/keys",
    },
    "openrouter": {
        "name": "OpenRouter",
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "description": "Access to 300+ models through one API. Pay-per-token.",
        "signup": "https://openrouter.ai/keys",
    },
    "zai": {
        "name": "Z.AI",
        "env_key": "ZAI_API_KEY",
        "base_url": "https://api.z.ai/api/v1",
        "description": "Z.AI platform. OpenAI-compatible endpoint.",
        "signup": "https://platform.z.ai",
    },
    "custom": {
        "name": "Custom",
        "env_key": "CUSTOM_API_KEY",
        "base_url": "http://localhost:8000/v1",
        "description": "Self-hosted or any OpenAI-compatible endpoint.",
        "signup": "",
    },
}


def _read_config() -> dict[str, Any]:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(cfg: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True, mode=0o700)
    # Ensure leaf directory also gets restrictive permissions
    os.chmod(os.path.dirname(CONFIG_PATH), 0o700)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)


def _detect_keys() -> dict[str, str | None]:
    """Scan environment for existing API keys."""
    found: dict[str, str | None] = {}
    for pid, info in PROVIDER_INFO.items():
        key = os.environ.get(info["env_key"])
        found[pid] = key
    return found


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "***"
    return key[:4] + "..." + key[-4:]


async def _test_connection(provider_id: str, api_key: str, base_url: str) -> tuple[bool, str]:
    """Test API connection. Returns (success, message)."""
    import httpx
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(f"{base_url}/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                count = len(data.get("data", []))
                return True, f"Connected successfully — {count} models available"
            elif resp.status_code == 401:
                return False, "Invalid API key — please check and try again"
            else:
                return False, f"Unexpected response: HTTP {resp.status_code}"
    except httpx.ConnectError:
        return False, "Cannot reach API server — check network or base URL"
    except httpx.TimeoutException:
        return False, "Connection timed out — server may be down"
    except Exception as e:
        return False, f"Connection test failed: {e}"


async def run_setup() -> None:
    """Run the interactive setup wizard."""
    _print_welcome()

    # Step 1: detect existing keys
    detected = _detect_keys()
    existing_config = _read_config()

    # Show providers table
    _print_providers_table(detected, existing_config)

    # Step 2: pick provider
    provider_id = _pick_provider(detected)
    info = PROVIDER_INFO[provider_id]

    # Step 3: get API key
    api_key = _get_api_key(provider_id, info, detected)

    # Step 4: test connection
    print()
    console.print("[bold]Testing connection...[/]", end=" ")
    ok, msg = await _test_connection(provider_id, api_key, info["base_url"])
    if ok:
        console.print(f"[#4ADE80]✓ {msg}[/]")
    else:
        console.print(f"[#F87171]✗ {msg}[/]")
        if not Confirm.ask("\nSave anyway? (you can test later)", default=False):
            console.print("[dim]Setup cancelled. Run `atar setup` to try again.[/]")
            return

    # Step 5: save
    cfg = _read_config()
    cfg["provider"] = provider_id
    cfg[f"{provider_id}_api_key"] = api_key
    _save_config(cfg)

    # Step 6: done
    _print_success(provider_id, info)


def _print_welcome() -> None:
    console.print()
    console.print(Panel.fit(
        "\n".join([
            "[bold #67D8FF]ATAR Setup Wizard[/]",
            "",
            "Configure your AI provider to get started.",
            "You'll need an API key from one of the supported providers.",
            "",
            "[dim]All configuration is stored locally at ~/.atar/config.json[/]",
        ]),
        border_style="#67D8FF",
        padding=(1, 2),
    ))
    console.print()


def _print_providers_table(detected: dict[str, str | None], existing: dict) -> None:
    table = Table(title="Available Providers", border_style="#394B59")
    table.add_column("#", style="dim", width=3)
    table.add_column("Provider", style="#67D8FF bold")
    table.add_column("Status", width=20)
    table.add_column("Description", style="dim")

    for i, (pid, info) in enumerate(PROVIDER_INFO.items()):
        key = detected.get(pid)
        cfg_key = existing.get(f"{pid}_api_key")
        if key:
            status = f"[#4ADE80]✓ Detected ({_mask_key(key)})[/]"
        elif cfg_key:
            status = "[#FBBF24]⚙ Saved in config[/]"
        else:
            status = "[dim]Not configured[/]"
        table.add_row(str(i + 1), info["name"], status, info["description"][:60])

    console.print(table)
    console.print()


def _pick_provider(detected: dict[str, str | None]) -> str:
    providers = list(PROVIDER_INFO.keys())
    default_idx = "1"  # DeepSeek

    # Pre-select if a key is already detected
    for i, pid in enumerate(providers):
        if detected.get(pid):
            default_idx = str(i + 1)
            break

    choice = Prompt.ask(
        "Select provider",
        choices=[str(i + 1) for i in range(len(providers))],
        default=default_idx,
    )
    return providers[int(choice) - 1]


def _get_api_key(provider_id: str, info: dict, detected: dict[str, str | None]) -> str:
    existing = detected.get(provider_id)
    if existing:
        console.print(f"\n[#4ADE80]API key detected from environment ({_mask_key(existing)})[/]")
        if Confirm.ask("Use this key?", default=True):
            return existing

    console.print(f"\n[bold]Enter your {info['name']} API key[/]")
    if info.get("signup"):
        console.print(f"[dim]Get one at: {info['signup']}[/]")

    while True:
        key = Prompt.ask(f"[{info['name']}] API key", password=True)
        if key.strip():
            return key.strip()
        console.print("[#F87171]API key cannot be empty[/]")


def _print_success(provider_id: str, info: dict) -> None:
    console.print()
    console.print(Panel.fit(
        "\n".join([
            "[bold #4ADE80]✓ Setup complete![/]",
            "",
            f"Provider: [bold]{info['name']}[/]",
            f"Config saved to: [dim]{CONFIG_PATH}[/]",
            "",
            "[bold]Next steps:[/]",
            "  • Run [bold #67D8FF]atar[/] to start the REPL",
            "  • Type [bold #67D8FF]/help[/] to see all commands",
            "  • Try [bold #67D8FF]atar doctor[/] to verify your setup",
        ]),
        border_style="#4ADE80",
        padding=(1, 2),
    ))
    console.print()
