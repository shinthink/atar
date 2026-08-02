# ATAR Security Checklist — v0.1

Status per 2026-08-02.

## Secrets
- [x] API keys resolved from env vars (not plaintext in code)
- [x] Config file (`~/.atar/config.yaml`) stores keys — WARNING: plaintext
- [ ] OS keyring integration (stub in SecretsManager, keyring lib optional)
- [ ] Encrypted secrets file

## Execution
- [x] All tool execution is local (no sandbox)
- [ ] Docker rootless sandbox (stub only)
- [ ] SSH remote execution (stub only)

## Approvals
- [x] Plan approval gate for high-risk tasks
- [x] Write file tool marked destructive (requires_approval=True)
- [ ] Runtime approval enforcement (flag checked but not enforced by CLI yet)

## Recovery
- [x] Session persistence (JSON file)
- [x] Memory persistence (JSON file)
- [ ] Automatic backup of state files
- [ ] Rollback of destructive operations
- [ ] Crash recovery with state restore

## Audit
- [x] Correlation IDs (atar_security/audit.py)
- [ ] Persistent audit log to file
- [ ] Redaction of secrets in logs

## Known Risks
1. API keys stored plaintext in config.yaml
2. No sandbox — tools run as current user
3. No network restrictions on web_fetch
4. Subagents share provider credentials

## Recovery Plan
1. All state stored in `.atar/` directory — backup this directory
2. Sessions stored as `.atar/sessions.json`
3. Memory stored as `.atar/memory.json`
4. Skills stored as `.atar/skills.json`
5. Evaluations stored as `.atar/evaluations.jsonl`
