"""Quick tests for vision tool, memory nudge wiring, skill improvement wiring."""

from __future__ import annotations

import os

import pytest
from atar_models.tools import ToolContext


class TestVisionTool:
    """analyze_image tool — basic validation tests (no real API)."""

    @pytest.mark.asyncio
    async def test_missing_path(self) -> None:
        from atar_tools.tools.vision import _analyze_image
        result = await _analyze_image("analyze_image", {}, ToolContext())
        assert not result.success
        assert "path required" in result.error

    @pytest.mark.asyncio
    async def test_file_not_found(self) -> None:
        from atar_tools.tools.vision import _analyze_image
        result = await _analyze_image("analyze_image", {"path": "/nonexistent/xyz.png"}, ToolContext())
        assert not result.success
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_with_prompt(self) -> None:
        """Should fail because no real provider, but validates args parsing."""
        # Create a tiny valid PNG
        import struct
        import zlib

        from atar_tools.tools.vision import _analyze_image

        # Minimal valid PNG
        def create_png(width=1, height=1):
            def chunk(chunk_type, data):
                c = chunk_type + data
                crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
                return struct.pack(">I", len(data)) + c + crc
            signature = b"\x89PNG\r\n\x1a\n"
            ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            raw = b""
            for _y in range(height):
                raw += b"\x00" + b"\xff\x00\x00" * width
            idat = chunk(b"IDAT", zlib.compress(raw))
            iend = chunk(b"IEND", b"")
            return signature + ihdr + idat + iend

        png_data = create_png()
        test_path = "/tmp/test_vision_temp.png"
        with open(test_path, "wb") as f:
            f.write(png_data)

        try:
            result = await _analyze_image("analyze_image", {"path": test_path, "prompt": "what is this?"}, ToolContext())
            # Will fail with provider error, but shouldn't be "file not found"
            assert result.error is None or "not found" not in result.error
        finally:
            os.unlink(test_path)


class TestToolRegistration:
    """Verify all new tools are registered."""

    def test_vision_tool_registered(self) -> None:
        from atar_tools.registry import list_all
        tools = {t.name for t in list_all()}
        assert "analyze_image" in tools

    def test_all_tools_count(self) -> None:
        from atar_tools.registry import list_all
        tools = list_all()
        assert len(tools) >= 19  # 12 original + 6 missing + 1 vision


class TestMemoryNudgeWired:
    """Verify memory nudge is wired into agent completion."""

    def test_nudge_check_doesnt_crash(self) -> None:
        """should_nudge() should not crash even without memory DB."""
        from atar_core.memory_nudge import should_nudge
        result = should_nudge()
        assert isinstance(result, bool)


class TestSkillImprovementWired:
    """Verify skill improvement tracking works."""

    def test_record_tracks_usage(self) -> None:
        from atar_core.skill_improvement import get_skill_stats, record_skill_use
        s = record_skill_use("wired-test-skill", success=True)
        assert s.times_used >= 1

        s2 = get_skill_stats("wired-test-skill")
        assert s2.times_used >= 1
