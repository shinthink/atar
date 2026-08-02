# ATAR Threat Model — v0.1

## THREAT-001: Prompt Injection via Skills/Plugins
- **Severity:** HIGH
- **Vector:** Malicious skill prompt or plugin hook injected into agent context
- **Impact:** Agent executes unintended commands, exfiltrates data
- **Mitigation:** Skill review gate (proposed→reviewed→active), plugin sandbox
- **Status:** Mitigated (manual review gate exists)

## THREAT-002: File Write Race Condition
- **Severity:** MEDIUM
- **Vector:** Concurrent agents write to same file
- **Impact:** Data corruption, lost work
- **Mitigation:** Checkpoint before write, sequential tool execution
- **Status:** Partially mitigated (checkpoint system)

## THREAT-003: Credential Leak via Model Response
- **Severity:** HIGH
- **Vector:** API key appears in model output or logs
- **Impact:** Credential exposure
- **Mitigation:** SecretsManager.redact(), provider resolves keys from env
- **Status:** Mitigated

## THREAT-004: Sandbox Escape via Tool Chaining
- **Severity:** MEDIUM
- **Vector:** chain web_fetch → write_file → terminal to execute remote code
- **Impact:** Remote code execution
- **Mitigation:** Approval gate on destructive tools, tool result size limits
- **Status:** Partially mitigated (approval enforcement)

## THREAT-005: Dependency Supply Chain
- **Severity:** LOW
- **Vector:** Malicious package in uv.lock
- **Impact:** Code execution during build
- **Mitigation:** pip-audit in CI, lockfile review
- **Status:** Not implemented
