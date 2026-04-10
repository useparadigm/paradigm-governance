# paradigm-governance

AST-based governance engine for enforcing module boundaries and architecture rules in Python codebases. Think [import-linter](https://github.com/seddonym/import-linter) but powered by [ast-grep](https://ast-grep.github.io/) for fast, accurate parsing.

Define your modules and allowed dependencies in a `governance.toml` file, then run checks in CI or locally. Detects circular dependencies, undeclared imports across module boundaries, layer violations, and reports module health metrics.

## Install

```bash
pip install paradigm-governance
```

## Quick Start

```bash
# Generate config from your project structure + real imports
governance-ast --generate --source-root src/

# Run governance checks
governance-ast

# Discover dependencies (no enforcement)
governance-ast --discover
```

## Config

```toml
[governance]
root = "src"
language = "python"

[[modules]]
name = "api"
path = "api/"
depends_on = ["core", "db"]
layer = "presentation"

[[modules]]
name = "core"
path = "core/"
depends_on = []
layer = "domain"

[[modules]]
name = "db"
path = "db/"
depends_on = ["core"]
layer = "infrastructure"

[layers]
order = ["presentation", "infrastructure", "domain"]

[rules]
no_cycles = true
enforce_layers = true
enforce_depends_on = true
exclude_test_files = true
```

### Rules

| Rule | Description |
|------|-------------|
| `no_cycles` | Detect circular dependencies between modules |
| `enforce_depends_on` | Flag imports not listed in `depends_on` |
| `enforce_layers` | Prevent lower layers importing higher ones |
| `max_public_surface` | Warn if too many symbols are used externally (float threshold) |
| `min_cohesion` | Warn if internal-to-total import ratio is too low (float threshold) |

## CI

### GitHub Action

```yaml
- uses: actions/checkout@v4
- name: Governance
  uses: useparadigm/paradigm-governance@main
  with:
    config: governance.toml
    diff: origin/main          # only check changed files
    advise: true               # LLM architectural advice
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}  # or ANTHROPIC_API_KEY
```

This posts a comment on your PR:

```
## ❌ Governance — 1 violation, 1 new module

🔴 🔗 core: Undeclared dependency: 'core' imports 'db' (allowed: [])
  core/service.py:2

📦 New module exporters (exporters/) — not in governance.toml

Reply /governance fix to apply.

🤖 AI: The core→db import creates tight coupling. Extract shared
types into a common module, or add "db" to core's depends_on.
```

All inputs:

| Input | Description | Default |
|-------|-------------|---------|
| `config` | Path to `governance.toml` | `governance.toml` |
| `diff` | Only check files changed since this ref | — |
| `baseline` | Path to baseline JSON | — |
| `advise` | LLM advice (needs API key in env) | `false` |
| `comment` | Post PR comment | `true` |

### `/governance fix` command

When the governance comment detects new modules, reply `/governance fix` on the PR to auto-apply the config update. The bot:

1. Reacts 👀 (acknowledged)
2. Adds new modules to `governance.toml` with `depends_on` populated from actual imports
3. Commits to your PR branch
4. Reacts 👍 and confirms

To enable this, add `.github/workflows/governance-fix.yml` to your repo:

```yaml
name: Governance Fix

on:
  issue_comment:
    types: [created]

permissions:
  contents: write
  pull-requests: write

jobs:
  apply-fix:
    name: Apply config fix
    runs-on: ubuntu-latest
    if: |
      github.event.issue.pull_request &&
      contains(github.event.comment.body, '/governance fix')
    steps:
      - name: Acknowledge
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh api repos/${{ github.repository }}/issues/comments/${{ github.event.comment.id }}/reactions \
            -X POST -f content=eyes

      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4

      - name: Checkout PR branch
        env:
          GH_TOKEN: ${{ github.token }}
        run: gh pr checkout ${{ github.event.issue.number }}

      - name: Find and apply fix
        id: fix
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          PAYLOAD=$(gh api repos/${{ github.repository }}/issues/${{ github.event.issue.number }}/comments \
            --jq '.[] | select(.body | contains("<!-- governance-fix:")) | .body' \
            | grep -oP '<!-- governance-fix:\K[A-Za-z0-9+/=]+' | tail -1)

          if [ -z "$PAYLOAD" ]; then
            gh api repos/${{ github.repository }}/issues/comments/${{ github.event.comment.id }}/reactions \
              -X POST -f content=confused
            exit 1
          fi

          DECODED=$(echo "$PAYLOAD" | base64 -d)
          CONFIG_PATH=$(echo "$DECODED" | python3 -c "import sys,json; print(json.load(sys.stdin)['config_path'])")
          echo "$DECODED" | python3 -c "import sys,json; print(json.load(sys.stdin)['updated_config'])" > "$CONFIG_PATH"

          pip install paradigm-governance
          governance-ast --config "$CONFIG_PATH" --fix-deps || true

          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add "$CONFIG_PATH"
          git diff --cached --quiet && exit 0

          git commit -m "governance: add new modules to config"
          git push
          echo "sha=$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT

      - name: Confirm
        if: steps.fix.outputs.sha
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh api repos/${{ github.repository }}/issues/comments/${{ github.event.comment.id }}/reactions \
            -X POST -f content='+1'
          gh pr comment ${{ github.event.issue.number }} \
            --body "✅ Config fix applied in \`${{ steps.fix.outputs.sha }}\`. Re-run checks to verify."
```

### Pre-commit

```yaml
repos:
  - repo: https://github.com/useparadigm/paradigm-governance
    rev: main
    hooks:
      - id: governance-check
      # or
      - id: governance-diff   # only changed files
```

### CLI in CI

```bash
governance-ast --diff origin/main
```

### Baseline workflow

```bash
# Save current violations as accepted
governance-ast --save-baseline .governance-baseline.json

# Only fail on new violations
governance-ast --baseline .governance-baseline.json
```

## LLM Advice

`--advise` calls an LLM to analyze violations and suggest fixes:

```bash
export OPENAI_API_KEY=sk-...   # or ANTHROPIC_API_KEY
governance-ast --advise
```

Supports OpenAI and Anthropic. Configure with env vars:

| Env var | Description |
|---------|-------------|
| `OPENAI_API_KEY` | Use OpenAI (default model: gpt-4o) |
| `ANTHROPIC_API_KEY` | Use Anthropic (default model: claude-sonnet-4-20250514) |
| `GOVERNANCE_LLM_PROVIDER` | Override: `openai` or `anthropic` |
| `GOVERNANCE_LLM_MODEL` | Override model name |

## Agent-Friendly

Ships with Claude Code skills in `.claude/skills/` that teach AI agents how to use the CLI and generate configs. See `governance.md` and `governance-config.md`.

## License

MIT
