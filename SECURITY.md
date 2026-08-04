# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in ATAR, please **do not open a public issue**. Instead, report it privately:

- **Email**: Create a GitHub Security Advisory at https://github.com/shinthink/atar/security/advisories/new
- **Response time**: We aim to respond within 48 hours
- **Disclosure**: We follow coordinated disclosure — you'll be credited when the fix is published

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.7.x   | ✅ Active |
| < 0.7   | ❌ No longer supported |

## Security Model

ATAR is an AI agent that executes tool calls on behalf of the user. The primary trust boundary is between the **AI model's instructions** and the **local execution environment**.

### What we protect against

- **Shell injection**: Terminal commands are validated against dangerous patterns (chaining, substitution, system writes)
- **Path traversal**: File read/write is workspace-bounded with `os.path.realpath()` checks
- **SSRF**: Web fetch blocks private/loopback IPs and revalidates redirect targets
- **Secret leakage**: Memory system filters API keys, tokens, and private keys
- **Unauthorized access**: Gateway (Telegram) has user allowlist

### What we don't protect against

- **AI prompt injection**: The agent trusts the model's output. If the model is jailbroken, it may attempt malicious commands (mitigated by command validation and approval gates)
- **Local privilege escalation**: ATAR runs with the user's permissions. File permissions on `~/.atar/` are set to 600/700
- **Denial of service**: Budget system limits turns/tools/time, but resource exhaustion is still possible

## Security Features

| Feature | Description |
|---------|-------------|
| Command validation | Blocks 14 dangerous shell patterns |
| Workspace bounding | `os.path.realpath()` + traversal + prefix check |
| SSRF protection | Blocks 9 private/loopback IP ranges + redirect revalidation |
| Secret filtering | Regex patterns for API keys, tokens, private keys |
| Approval gates | 5-choice interactive approval with diff preview |
| Budget system | Limits turns, tools, time, repeated calls |
| Safe environment | Minimal env passed to subprocess (no host secrets) |
| Config permissions | `chmod 600` on config files, `700` on directories |

## Audit History

- **2026-08-04**: Full source audit — 12 findings, all resolved
- **2026-07**: P0/P1 repair — tool hardening, protocol fixes
