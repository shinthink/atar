"""Tests for setup wizard — pure functions only (no interactive prompts)."""

from __future__ import annotations

import os

import pytest


class TestSetupWizardHelpers:
    """Pure helper functions in setup_wizard."""

    def test_detect_keys_finds_env_vars(self) -> None:
        os.environ["DEEPSEEK_API_KEY"] = "sk-test-detect"
        try:
            from atar_cli.setup_wizard import _detect_keys
            keys = _detect_keys()
            assert keys["deepseek"] == "sk-test-detect"
        finally:
            del os.environ["DEEPSEEK_API_KEY"]

    def test_detect_keys_empty(self) -> None:
        from atar_cli.setup_wizard import _detect_keys
        # Clear any existing env keys for this test
        for env_key in ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                         "OPENROUTER_API_KEY", "ZAI_API_KEY", "CUSTOM_API_KEY"]:
            os.environ.pop(env_key, None)
        keys = _detect_keys()
        for pid in ["deepseek", "openai", "anthropic", "openrouter", "zai", "custom"]:
            assert pid in keys
            assert keys[pid] == ""  # empty string when no env var

    def test_mask_key_short(self) -> None:
        from atar_cli.setup_wizard import _mask_key
        assert _mask_key("sk-abc") == "***"

    def test_mask_key_long(self) -> None:
        from atar_cli.setup_wizard import _mask_key
        masked = _mask_key("sk-1234567890abcdef")
        assert masked.startswith("sk-1")
        assert masked.endswith("cdef")
        assert "..." in masked

    def test_read_config_empty(self) -> None:
        from atar_cli.setup_wizard import CONFIG_PATH, _read_config
        if os.path.exists(CONFIG_PATH):
            os.unlink(CONFIG_PATH)
        cfg = _read_config()
        assert isinstance(cfg, dict)

    def test_save_and_read_config(self) -> None:
        from atar_cli.setup_wizard import CONFIG_PATH, _read_config, _save_config
        backup = None
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                backup = f.read()
        try:
            _save_config({"provider": "deepseek", "deepseek_api_key": "sk-test-123"})
            cfg = _read_config()
            assert cfg["provider"] == "deepseek"
            assert cfg["deepseek_api_key"] == "sk-test-123"
            # Verify permissions
            stat = os.stat(CONFIG_PATH)
            assert stat.st_mode & 0o777 == 0o600
        finally:
            if backup is not None:
                with open(CONFIG_PATH, "w") as f:
                    f.write(backup)


class TestProviderInfo:
    """Provider data completeness."""

    def test_all_providers_have_required_fields(self) -> None:
        from atar_cli.setup_wizard import PROVIDER_INFO
        required = ["name", "env_key", "base_url"]
        for pid, info in PROVIDER_INFO.items():
            for field in required:
                assert field in info, f"{pid} missing {field}"

    def test_providers_have_unique_env_keys(self) -> None:
        from atar_cli.setup_wizard import PROVIDER_INFO
        keys = [info["env_key"] for info in PROVIDER_INFO.values()]
        assert len(keys) == len(set(keys)), "Duplicate env keys found"


class TestConnectionTest:
    """Connection test edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_key(self) -> None:
        from atar_cli.setup_wizard import _test_connection
        ok, msg = await _test_connection("deepseek", "invalid-key", "https://api.deepseek.com/v1")
        assert not ok
        assert "Invalid" in msg or "key" in msg.lower() or "fail" in msg.lower()

    @pytest.mark.asyncio
    async def test_unreachable_host(self) -> None:
        from atar_cli.setup_wizard import _test_connection
        ok, msg = await _test_connection("custom", "sk-test", "http://127.0.0.1:19999")
        assert not ok


class TestSetupConfig:
    """Config save/load with permissions."""

    def test_config_permissions_restrictive(self) -> None:

        from atar_cli.setup_wizard import CONFIG_PATH, _save_config
        backup = None
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                backup = f.read()
        try:
            _save_config({"test": True})
            mode = os.stat(CONFIG_PATH).st_mode
            # Should not be world-readable
            assert mode & 0o007 == 0
        finally:
            if backup is not None:
                with open(CONFIG_PATH, "w") as f:
                    f.write(backup)
