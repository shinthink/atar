# ATAR Runbooks

## Backup
```bash
cp -r ~/.atar ~/.atar.backup.$(date +%Y%m%d)
```

## Restore
```bash
cp -r ~/.atar.backup.YYYYMMDD ~/.atar
```

## Upgrade
```bash
cd ATAR-Project && git pull && uv sync
```

## Rollback
```bash
cd ATAR-Project && git checkout v0.1.0 && uv sync
```

## Reset
```bash
rm -rf .atar/sessions.json .atar/memory.json .atar/skills.json
```

## Debug
```bash
# Enable verbose output
export ATAR_LOG_LEVEL=DEBUG
atar chat "test"

# Test with fake provider (no API key needed)
atar chat "hello"
```
