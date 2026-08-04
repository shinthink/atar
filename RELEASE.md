# Release Process

## Publishing to PyPI

ATAR uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — no API tokens needed.

### One-time setup

1. Create PyPI account at https://pypi.org
2. Create project `atar-agent` at https://pypi.org/manage/projects/
3. Configure Trusted Publishing:
   - Owner: `shinthink`, Repo: `shinthink/atar`, Workflow: `publish.yml`

### Release

```bash
git tag v0.7.0
git push origin main --tags
```

GitHub Actions builds and publishes automatically.

### Install

```bash
pip install atar-agent
```
