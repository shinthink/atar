# Research: OpenAI Responses API

## Metadata
- **Research date:** 2026-08-01
- **Official documentation URL:** https://platform.openai.com/docs/api-reference/responses
- **Streaming URL:** https://platform.openai.com/docs/api-reference/responses-streaming
- **Research owner:** Lead Architect

## Purpose
Provider #2 for ATAR. OpenAI uses the Responses API (newer, stateful) or Chat Completions API (legacy).

## Authentication
- Header: `Authorization: Bearer $OPENAI_API_KEY`
- Env: `OPENAI_API_KEY`

## Base URL
- Default: `https://api.openai.com/v1/responses`

## API Mode
`openai_responses` — OpenAI Responses API

## Required Headers
- `Authorization: Bearer $OPENAI_API_KEY`
- `Content-Type: application/json`
- Optional: `OpenAI-Organization`, `OpenAI-Project`

## Request Format
```json
{
  "model": "gpt-5",
  "input": "Hello world",
  "instructions": "System prompt here",
  "tools": [{"type": "function", "name": "...", "parameters": {...}}],
  "tool_choice": "auto",
  "stream": true,
  "max_output_tokens": 4096
}
```

## Streaming
- Protocol: SSE
- Events: `response.created`, `response.in_progress`, `response.output_text.delta`, `response.output_text.done`, `response.completed`
- Text appears as `response.output_text.delta` events
- Tool calls appear as `response.output_item.added` + function call arguments
- HTTP 202 for async processing

## Tool Calling
- Define: `tools` array with `type: "function"`, `name`, `parameters`
- Response: tool calls in output with `type: "function_call"`
- Tool results must be submitted back

## Error Handling
- HTTP 429: Rate limited — retry with `Retry-After`
- HTTP 401: Invalid key
- HTTP 500: Server error

## Rate Limits
- Tier-based: Free (3 RPM), Tier 1-5
- TPM limits scale with tier

## ATAR Adapter Mapping
- `ModelProvider.complete()` → POST `/v1/responses`
- `ModelProvider.stream()` → POST `/v1/responses` with `stream: true`
- `ModelProvider.count_tokens()` → Not natively supported — estimate or skip
- `ModelProvider.list_models()` → GET `/v1/models`
