# Research: Anthropic Messages API

## Metadata
- **Research date:** 2026-08-01
- **Official documentation URL:** https://docs.anthropic.com/en/api/messages
- **Streaming URL:** https://docs.anthropic.com/en/api/messages-streaming
- **SDK version:** anthropic-sdk-python (latest)
- **Research owner:** Lead Architect

## Purpose
Primary provider for ATAR. Anthropic is the reference provider per blueprint Section 6.

## Authentication
- Header: `x-api-key: $ANTHROPIC_API_KEY`
- Also supports: `anthropic-api-key: $ANTHROPIC_API_KEY` (deprecated)
- Env: `ANTHROPIC_API_KEY`
- Bearer NOT supported for API key (only for OAuth/SSO)

## Base URL
- Default: `https://api.anthropic.com/v1/messages`
- AWS Bedrock: `https://bedrock-runtime.{region}.amazonaws.com`
- Google Vertex AI: `https://{region}-aiplatform.googleapis.com`

## API Mode
`anthropic_messages` — native Anthropic Messages API

## Required Headers
- `x-api-key`
- `anthropic-version: 2023-06-01`
- `content-type: application/json`
- Optional: `anthropic-beta` for beta features

## Request Format
```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 1024,
  "messages": [{"role": "user", "content": "Hello"}],
  "system": "Optional system prompt",
  "tools": [{"name": "...", "description": "...", "input_schema": {...}}],
  "tool_choice": {"type": "auto"},
  "stream": true,
  "temperature": 1.0,
  "thinking": {"type": "enabled", "budget_tokens": 1024}
}
```

## Streaming
- Protocol: SSE (Server-Sent Events)
- Events: `message_start`, `content_block_start`, `content_block_delta` (text_delta, input_json_delta), `content_block_stop`, `message_delta`, `message_stop`, `ping`
- Text appears as `content_block_delta` with `delta.type: "text_delta"` and `delta.text`
- Tool call JSON appears as `content_block_delta` with `delta.type: "input_json_delta"` and `delta.partial_json`
- Thinking: `content_block_start(thinking)` → `content_block_delta(thinking_delta)` → `content_block_stop`

## Tool Calling
- Define: `tools` array with `name`, `description`, `input_schema`
- Response: `content_block` with `type: "tool_use"`, `id`, `name`, `input`
- Parallel tool use: enabled by default
- Strict tool use: `tool_choice: {"type": "any"}`
- Tool results must be returned as `role: "user"` messages with `tool_result` content blocks

## Error Handling
- HTTP 429: Rate limited — exponential backoff with `Retry-After` header
- HTTP 529: Overloaded — retry with backoff
- HTTP 400: Invalid request
- HTTP 401: Invalid API key
- HTTP 413: Request too large
- HTTP 500: Server error — retry

## Rate Limits
- Tier-based: Build (1K RPM), Scale (2K RPM), Business (4K RPM)
- TPM limits: model-dependent
- Headers: `anthropic-ratelimit-requests-limit`, `-remaining`, `-reset`

## Capability Matrix
| Capability | Supported |
|-----------|-----------|
| Text generation | Yes |
| Streaming | Yes (SSE) |
| Tool calling | Yes |
| Thinking/reasoning | Yes |
| Vision | Yes (images) |
| PDF support | Yes |
| Prompt caching | Yes |
| Batch processing | Yes |
| Structured output | Yes |

## ATAR Adapter Mapping
- `ModelProvider.complete()` → POST `/v1/messages` with `stream: false`
- `ModelProvider.stream()` → POST `/v1/messages` with `stream: true`, parse SSE
- `ModelProvider.count_tokens()` → POST `/v1/messages/count_tokens`
- `ModelProvider.list_models()` → GET `/v1/models`
