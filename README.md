# code-governance

**Enforce module boundaries in Python. Catch architectural violations in CI.**

```
$ governance-ast
Governance Report (python)
Modules: 5 | Files scanned: 47

Violations (2):
  [E] [enforce_depends_on] Undeclared dependency: 'api' imports 'billing' (allowed: ['core', 'auth'])
      api/checkout.py:3    from billing.stripe import charge_customer
  [E] [no_cycles] Circular dependency: payments -> notifications -> payments
      payments/process.py:1    from notifications.email import send_receipt

FAILED
```

Define allowed dependencies between modules in a `governance.toml`. Run it locally, in CI, or let an LLM tell you what to fix.

## Why

Codebases rot from the inside. One "quick" import across a module boundary becomes ten, and suddenly everything depends on everything. Tests break for no reason, refactors are impossible, and new developers can't tell where one module ends and another begins.

`code-governance` makes module boundaries explicit and enforced. Like a linter for your architecture.

## Quick start with Claude Code

The fastest way to get started — the plugin handles everything interactively:

```
/plugin marketplace add useparadigm/code-governance-plugin
/plugin install code-governance
/governance-init
```

Claude scans your codebase, asks about your architecture, creates `governance.toml`, and sets up CI. See the [plugin repo](https://github.com/useparadigm/code-governance-plugin) for details.

## Install (manual)

```bash
pip install code-governance
```

## 30-second setup

```bash
# Generate config from your project — detects modules, maps real imports
governance-ast --generate --source-root src/

# See what you've got
governance-ast --discover

# Enforce it
governance-ast
```

This creates a `governance.toml`:

```toml
[governance]
root = "src"
language = "python"

[[modules]]
name = "api"
path = "api/"
depends_on = ["core", "auth"]
layer = "presentation"

[[modules]]
name = "core"
path = "core/"
depends_on = []
layer = "domain"

[[modules]]
name = "auth"
path = "auth/"
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

## What it catches

| Rule | What it does |
|------|-------------|
| `enforce_depends_on` | Module imports something not in its `depends_on` list |
| `no_cycles` | A imports B imports A |
| `enforce_layers` | Lower layer imports from a higher one |
| `max_public_surface` | Too many symbols exposed to other modules (float threshold) |
| `min_cohesion` | Module imports more externally than internally (float threshold) |

## CI

### GitHub Action

```yaml
- uses: actions/checkout@v4
- name: Governance
  uses: useparadigm/code-governance@main
  with:
    config: governance.toml
    diff: origin/main
    advise: true
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

Posts a comment on your PR:

```
❌ Governance — 1 violation, 1 new module

🔴 🔗 core: Undeclared dependency: 'core' imports 'db' (allowed: [])
  core/service.py:2

📦 New module exporters (exporters/) — not in governance.toml

Reply /governance fix to apply.

🤖 AI: The core→db import creates tight coupling. Extract shared
types into a common module, or add "db" to core's depends_on.
```

| Input | Description | Default |
|-------|-------------|---------|
| `config` | Path to `governance.toml` | `governance.toml` |
| `diff` | Only check files changed since this ref | — |
| `baseline` | Path to baseline JSON | — |
| `advise` | LLM architectural advice (needs API key) | `false` |
| `comment` | Post PR comment | `true` |

### `/governance fix`

When new modules are detected, reply `/governance fix` on the PR. The bot adds them to `governance.toml` with `depends_on` auto-populated from actual imports, and commits to your branch.

To enable, add [`.github/workflows/governance-fix.yml`](#governance-fix-workflow) to your repo.

### Pre-commit

```yaml
repos:
  - repo: https://github.com/useparadigm/code-governance
    rev: main
    hooks:
      - id: governance-check
      - id: governance-diff   # only changed files
```

### Baseline workflow

Adopting on an existing codebase? Accept current violations, only fail on new ones:

```bash
governance-ast --save-baseline .governance-baseline.json
governance-ast --baseline .governance-baseline.json
```

## HTML report

```bash
governance-ast --format html > report.html
```

Self-contained file with a dependency matrix (modules x modules heatmap, cycles highlighted) and module detail view. Also works as a standalone viewer — drop any governance JSON into it.

## LLM advice

```bash
export OPENAI_API_KEY=sk-...   # or ANTHROPIC_API_KEY
governance-ast --advise
```

Analyzes your violations with an LLM and suggests whether to accept the dependency, restructure the code, or extract a shared module. Works with OpenAI and Anthropic.

| Env var | Description |
|---------|-------------|
| `OPENAI_API_KEY` | OpenAI (default: gpt-4o) |
| `ANTHROPIC_API_KEY` | Anthropic (default: claude-sonnet-4-20250514) |
| `GOVERNANCE_LLM_MODEL` | Override model |

## vs import-linter

[import-linter](https://github.com/seddonym/import-linter) is the established tool for this. Here's an honest comparison:

| | code-governance | import-linter |
|---|---|---|
| **Setup** | `--generate` creates config from source | Manual contract definition |
| **Config format** | TOML (governance.toml) | INI or TOML |
| **Rules** | depends_on, cycles, layers, cohesion, surface | independence, layers, forbidden, acyclic siblings |
| **Diff mode** | `--diff HEAD` — only check changed files | No |
| **Baseline** | Accept existing violations, fail on new | No |
| **CI comments** | PR comments with violations + fix suggestions | No |
| **Auto-fix** | `/governance fix` applies config updates | No |
| **LLM advice** | `--advise` — architectural recommendations | No |
| **HTML report** | Dependency matrix + module detail viewer | Browser UI (separate) |
| **JSON output** | Yes | No |
| **Module metrics** | Cohesion, public surface, symbol count | No |
| **Indirect imports** | Direct only | Transitive chains |
| **Parser** | ast-grep (Rust) | grimp (compiled) |
| **Speed (Django, 902 files)** | ~1.2s | ~0.1s |
| **Package needs installing** | No — scans source files directly | Yes — must be importable |
| **Agent-friendly** | Claude Code skills included | No |

**Choose import-linter if** you need transitive import detection or forbidden contracts. **Choose code-governance if** you want CI integration, auto-fix, LLM advice, metrics, or zero-config setup.

## Agent-friendly

Ships with Claude Code skills in `.claude/skills/` that teach AI coding agents how to run checks, interpret violations, and generate configs.

---

## Appendix

### Governance fix workflow

Add this to `.github/workflows/governance-fix.yml` to enable the `/governance fix` command:

<details>
<summary>governance-fix.yml</summary>

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

          pip install code-governance
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

</details>

## License

MIT
