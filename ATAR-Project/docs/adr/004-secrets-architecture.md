# ADR-004: Secrets Architecture

## Status
Accepted

## Context
Per blueprint Section 6.13, ATAR must handle API keys and other secrets securely. The priority order is: OS keyring → external secrets provider plugin → process environment variables → encrypted local secrets file protected by user passphrase.

Secrets must never be stored plaintext in SQLite, logs, prompts, session history, memory, crash reports, command history, tool containers, or plugin APIs.

## Decision
Implement a **pluggable secrets backend** with two initial implementations: `KeyringBackend` (primary) and `EnvFileBackend` (fallback).

### Architecture
```
atar_security/
├── secrets.py        — SecretsManager with backend selection
├── backends/
│   ├── keyring.py    — OS keyring via keyring library
│   └── env_file.py   — Encrypted .env file fallback
└── secret_ref.py     — SecretRef type for config references
```

### Backend Priority
1. **KeyringBackend** — uses `keyring` library (macOS Keychain, Linux Secret Service/kwallet, Windows Credential Manager)
2. **EnvFileBackend** — reads from encrypted `.atar/secrets.env` file or process environment
3. **Explicit env vars** — `ATAR_*_API_KEY` environment variables as last resort

### Secret References
Configuration files reference secrets by URI, never by value:
```yaml
providers:
  anthropic:
    secret_ref: "keyring://atar/providers/anthropic/default"
```

### Secret Redaction
All loggers, crash reporters, and audit writers must call `SecretsManager.redact(text)` before storing or displaying any text that might contain credential material.

## Consequences
- API keys never appear in config files, logs, or database.
- Users can choose between system keyring (secure) or env vars (simple).
- Provider testing must resolve secrets before making API calls.
- Backup/restore must handle secrets separately from database state.

## Alternatives Considered
1. **Plaintext in config.yaml** — rejected (Section 6.13 prohibition).
2. **Hardcoded environment variable only** — rejected because it provides no keyring integration.
3. **External vault (HashiCorp Vault, AWS Secrets Manager)** — rejected for v1.0 local-only product.

## References
- Blueprint Section 6.13 (Secrets handling)
- Blueprint Section 12 (Security and Permission System)
- https://pypi.org/project/keyring/
- https://docs.python.org/3/library/os.html#os.environ
