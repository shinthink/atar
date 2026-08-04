"""ATAR vision tool — analyze images via AI provider vision capabilities."""

from __future__ import annotations

import base64
from typing import Any

from atar_models.requests import Message, ModelRequest
from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register


async def _analyze_image(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Analyze an image using the configured AI provider's vision capabilities."""
    path = args.get("path", "")
    prompt = args.get("prompt", "Describe this image in detail.")

    if not path:
        return ToolResult(success=False, error="path required")

    import os

    if not os.path.exists(path):
        return ToolResult(success=False, error=f"File not found: {path}")

    # Read and encode image
    try:
        with open(path, "rb") as f:
            image_data = f.read()

        # Determine MIME type
        ext = os.path.splitext(path)[1].lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        mime_type = mime_map.get(ext, "image/png")

        # Base64 encode
        b64 = base64.b64encode(image_data).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64}"

        # Check size — most vision APIs have 20MB limit
        if len(image_data) > 20 * 1024 * 1024:
            return ToolResult(success=False, error="Image too large (>20MB)")
    except Exception as e:
        return ToolResult(success=False, error=f"Failed to read image: {e}")

    # Get default provider for vision
    try:
        from atar_core.provider_router import create_router
        router = create_router()
        provider = router.providers[0] if router.providers else None
        if not provider:
            return ToolResult(success=False, error="No AI provider configured")

        # Build vision request — use raw dict to bypass Pydantic content validation
        req = ModelRequest(
            provider_id="atar",
            model=getattr(provider, "model", "gpt-4o"),
            messages=[
                Message(
                    role="user",
                    content=f"{prompt}\n\n[Image data URL: {data_url}]",
                ),
            ],
            tools=[],
        )

        # Stream response
        text_parts: list[str] = []
        async for event in provider.stream(req):
            if hasattr(event, "event_type") and event.event_type == "text_delta" and hasattr(event, "text") and event.text:
                    text_parts.append(event.text)

        result_text = "".join(text_parts).strip()
        if not result_text:
            return ToolResult(success=False, error="Provider returned empty response (may not support vision)")

        return ToolResult(
            success=True,
            output=result_text,
            metadata={
                "path": path,
                "size_bytes": len(image_data),
                "mime_type": mime_type,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=f"Vision analysis failed: {e}")


register(
    "analyze_image",
    "Analyze an image using AI vision (GPT-4V, Claude, etc.)",
    _analyze_image,
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to image file (PNG, JPG, GIF, WebP)"},
            "prompt": {"type": "string", "description": "What to analyze in the image (default: describe)"},
        },
        "required": ["path"],
    },
    max_output_chars=5000,
    destructive=False,
    toolset="vision",
)
