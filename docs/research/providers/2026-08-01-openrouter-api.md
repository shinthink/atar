# Research: OpenRouter API

## Metadata
- **Research date:** 2026-08-01
- **Official documentation URL:** https://openrouter.ai/docs
- **Research owner:** Lead Architect

## Purpose
Provider #5 for ATAR. Gateway to 200+ models across providers.

## Authentication
- Header: `Authorization: Bearer $OPENROUTER_API_KEY`
- Env: `OPENROUTER_API_KEY`

## Base URL
- `https://openrouter.ai/api/v1/chat/completions`

## API Mode
`openai_chat_compatible` — with extra headers

## Unique Features
- Model slugs: `openai/gpt-5`, `anthropic/claude-sonnet-4`, `deepseek/deepseek-v4`
- Model routing preferences via headers
- Price tracking in response headers
- Provider fallback configuration

## Required Headers
- `Authorization: Bearer $OPENROUTER_API_KEY`
- `HTTP-Referer`: ATAR app URL
- `X-Title`: "ATAR Terminal"

## Tool Calling
- Pass-through to underlying provider
- Quality depends on selected model

## ATAR Adapter Mapping
Use OpenAI Chat Completions adapter with OpenRouter base URL.
