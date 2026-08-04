"""Plugin system tests."""

from __future__ import annotations


class TestPluginDiscovery:
    """Plugin auto-discovery."""

    def test_discover_plugins(self) -> None:
        from plugins import discover_plugins
        result = discover_plugins()
        assert isinstance(result, dict)
        # Result may be empty if no plugin packages found — that's valid

    def test_load_all_graceful(self) -> None:
        from plugins import load_all
        result = load_all()
        assert isinstance(result, dict)

    def test_load_nonexistent_plugin(self) -> None:
        from plugins import load_plugin
        result = load_plugin("tools", "nonexistent_plugin_xyz")
        assert result is None
