"""M1 tests — configuration, profiles, paths, bootstrap."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_home():
    """Isolated ATAR_HOME for tests."""
    with tempfile.TemporaryDirectory() as td:
        old = os.environ.get("ATAR_HOME")
        os.environ["ATAR_HOME"] = td
        try:
            yield Path(td)
        finally:
            if old:
                os.environ["ATAR_HOME"] = old
            else:
                del os.environ["ATAR_HOME"]


class TestConfig:
    """Configuration system tests."""

    def test_config_creates_default(self, temp_home) -> None:
        """First load creates default config files."""
        from atar_core.config import load_config
        config = load_config("default")
        assert config.config_path.exists()
        assert config.raw["model"]["provider"] == "deepseek"
        assert config.raw["agent"]["max_turns"] == 8

    def test_profile_isolation(self, temp_home) -> None:
        """Different profiles have separate configs."""
        import os
        from atar_core.config import load_config, save_config
        os.environ["ATAR_HOME"] = str(temp_home)
        cfg_a = load_config("profile_isolation_a")
        cfg_a.raw["model"]["provider"] = "openai"
        save_config(cfg_a)

        cfg_b = load_config("profile_isolation_b")
        assert cfg_b.raw["model"]["provider"] == "deepseek"  # default
        assert cfg_a.config_path != cfg_b.config_path

    def test_config_merge_preserves_defaults(self, temp_home) -> None:
        """Partial config files merge with defaults."""
        from atar_core.config import load_config, save_config, atar_config_file
        import os, yaml
        # Ensure isolated
        os.environ["ATAR_HOME"] = str(temp_home)
        # Write partial config
        path = atar_config_file("merge_test")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.safe_dump({"model": {"temperature": 0.2}}, f)

        cfg = load_config("merge_test")
        assert cfg.raw["model"]["temperature"] == 0.2  # overridden
        assert cfg.raw["model"]["provider"] == "deepseek"  # default preserved
        assert cfg.raw["agent"]["max_turns"] == 8  # default preserved


class TestPaths:
    """Path resolution tests."""

    def test_atarcd(self, temp_home) -> None:
        """Paths resolve under ATAR_HOME."""
        from atar_core.paths import atar_config_dir, atar_data_dir, atar_skills_dir
        assert str(temp_home) in str(atar_config_dir())
        assert str(temp_home) in str(atar_data_dir())

    def test_profile_paths_differ(self, temp_home) -> None:
        """Profile paths are distinct."""
        from atar_core.paths import atar_config_dir
        a = atar_config_dir("one")
        b = atar_config_dir("two")
        assert a != b

    def test_ensure_dirs_creates_all(self, temp_home) -> None:
        """ensure_dirs creates required directories."""
        from atar_core.paths import ensure_dirs, atar_data_dir, atar_skills_dir
        ensure_dirs("test")
        assert atar_data_dir("test").exists()
        assert atar_skills_dir("test").exists()
