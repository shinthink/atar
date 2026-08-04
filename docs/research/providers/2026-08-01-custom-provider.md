# Research: Custom Provider

## Metadata
- **Research date:** 2026-08-01
- **Research owner:** Lead Architect
- **Status:** Specification — no external docs to retrieve

## Purpose
Provider #6 per Section 6.5. Allows users to connect any OpenAI-compatible or Anthropic-compatible endpoint.

## Authentication
- 8 supported types: `bearer`, `api_key`, `x_api_key`, `basic`, `oauth2`, `env`, `none`, `custom_header`
- User provides: base URL, auth type, auth value, API mode

## API Modes
- `openai_chat_compatible` — sends to `{base_url}/chat/completions`
- `anthropic_messages` — sends to `{base_url}/messages`
- `openai_responses` — sends to `{base_url}/responses`

## Compliance Requirements (Section 6.10)
- Must pass all ModelProvider contract tests before marked "verified"
- Unverified providers show warning badge in TUI
- Capability matrix auto-probed: stream, tools, token count, model list

## ATAR Implementation
Single `CustomProvider` adapter that switches behavior based on `api_mode` configuration.
Capability probe sequence runs on first use.
