# Research: DeepSeek API

## Metadata
- **Research date:** 2026-08-01
- **Official documentation URL:** https://api-docs.deepseek.com/
- **Research owner:** Lead Architect

## Purpose
Provider #3 for ATAR. DeepSeek supports both OpenAI-compatible AND Anthropic-compatible formats.

## Authentication
- Header: `Authorization: Bearer $DEEPSEEK_API_KEY`
- Env: `DEEPSEEK_API_KEY`

## Base URL
- OpenAI format: `https://api.deepseek.com/v1`
- Anthropic format: `https://api.deepseek.com/anthropic`

## API Modes
- `openai_chat_compatible` — Chat Completions at `/v1/chat/completions`
- `anthropic_messages` — Messages at `/anthropic/messages`

## Anthropic Format Support
Per official docs (retrieved 2026-08-01):
- `x-api-key` header: FULLY SUPPORTED
- `anthropic-version`, `anthropic-beta`: IGNORED (safe to omit)
- `content` as STRING: FULLY SUPPORTED
- `content` as array: FULLY SUPPORTED
- `system` field: FULLY SUPPORTED
- `tools` with `name`, `input_schema`, `description`: FULLY SUPPORTED
- `stream`: FULLY SUPPORTED
- `tool_choice`: SUPPORTED
- `thinking`: NOT SUPPORTED (or limited)
- `prompt_caching`: NOT SUPPORTED
- Unsupported model names mapped to default model

## Streaming (Anthropic format)
- SSE with event types: `message_start`, `content_block_start`, `content_block_delta`, `message_delta`, `message_stop`

## Error Handling
- Standard HTTP errors
- Rate limit headers: standard

## Unresolved
- Exact feature matrix vs Anthropic needed (Section 6.5 requirement)
- Model listing endpoint behavior
- Thinking/reasoning support status

## ATAR Approach
Use Anthropic adapter for DeepSeek with `base_url: "https://api.deepseek.com/anthropic"`. 
This gives us one adapter that works for both Anthropic-native and DeepSeek-Anthropic endpoints.
