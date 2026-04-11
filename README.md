<p align="center">
  <img src="code-governance.jpg" alt="code-governance" width="200">
</p>

<h1 align="center">code-governance</h1>

<p align="center"><b>Stop spaghetti imports. Enforce module boundaries in Python.</b></p>

<p align="center">
  <a href="https://pypi.org/project/code-governance/"><img src="https://img.shields.io/pypi/v/code-governance?style=flat&color=orange" alt="PyPI"></a>
  <a href="https://github.com/useparadigm/code-governance/actions"><img src="https://img.shields.io/github/actions/workflow/status/useparadigm/code-governance/tests.yml?style=flat&label=tests" alt="Tests"></a>
  <a href="https://github.com/useparadigm/code-governance/blob/main/LICENSE"><img src="https://img.shields.io/github/license/useparadigm/code-governance?style=flat" alt="License"></a>
</p>

---

## Before / After

| Without governance | With governance |
|---|---|
| `api/` imports from `billing/`, `db/`, `auth/`, `utils/`, `migrations/`... | `api/` imports from `core/`, `auth/` — nothing else allowed |
| One refactor breaks 14 files across 6 modules | Boundaries are explicit, changes stay local |
| New dev: "Can I import this here?" "Uhh... maybe?" | Config says yes or no. CI enforces it. |

## Zero-config scan

No setup needed. Point it at your code:

```bash
$ pip install code-governance
$ governance-ast --auto src/

Governance Report (python)
Modules: 8 | Files scanned: 47

Violations (1):
  [E] [no_cycles] Circular dependency: payments -> notifications -> payments

FAILED
```

Found a cycle in 1.2 seconds. No config file. No contract definitions.

## Quick start with Claude Code

The fastest path — the plugin handles everything interactively:

```
/plugin marketplace add useparadigm/code-governance-plugin
/plugin install code-governance
/governance-init
```

Claude scans your codebase, asks about your architecture, creates config, and sets up CI.

## Manual setup

```bash
pip install code-governance

# Generate config from your project — detects modules, maps real imports
governance-ast --generate --source-root src/

# See the dependency map
governance-ast --discover

# Enforce it
governance-ast
```

## What it catches

| Rule | Example |
|------|---------|
| `enforce_depends_on` | `api` imports `billing` but only `core`, `auth` are allowed |
| `no_cycles` | `payments` -> `notifications` -> `payments` |
| `enforce_layers` | `db` (infrastructure) imports from `api` (presentation) |
| `max_public_surface` | 80% of `core`'s symbols used externally — too exposed |
| `min_cohesion` | `utils` imports 90% from other modules — grab-bag module |

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

PR comment:

```
❌ Governance — 1 violation, 1 new module

🔴 🔗 core: Undeclared dependency: 'core' imports 'db' (allowed: [])
  core/service.py:2

📦 New module exporters (exporters/) — not in governance.toml

Reply /governance fix to apply.

🤖 AI: The core→db import creates tight coupling. Extract shared
types into a common module, or add "db" to core's depends_on.
```

### `/governance fix`

Reply `/governance fix` on a PR → bot adds new modules to config, populates `depends_on` from actual imports, commits to your branch. [Setup](#governance-fix-workflow)

### Pre-commit

```yaml
repos:
  - repo: https://github.com/useparadigm/code-governance
    rev: main
    hooks:
      - id: governance-check
      - id: governance-diff
```

### Adopting on legacy codebases

```bash
governance-ast --save-baseline .governance-baseline.json
governance-ast --baseline .governance-baseline.json
```

Accept existing violations. Only fail on new ones.

## LLM advice

```bash
export OPENAI_API_KEY=sk-...   # or ANTHROPIC_API_KEY
governance-ast --advise
```

Analyzes violations and suggests: accept the dependency, restructure the code, or extract a shared module. Works with OpenAI and Anthropic.

## HTML report

```bash
governance-ast --format html > report.html
```

Self-contained dependency matrix with module metrics. Drop any governance JSON into it.

## vs import-linter

| | code-governance | import-linter |
|---|---|---|
| **Setup** | `--auto` or `--generate` — zero to minimal config | Manual contract definition |
| **Zero-config scan** | `--auto src/` — instant results | No |
| **Diff mode** | `--diff HEAD` — only changed files | No |
| **Baseline** | Accept existing violations, fail on new | No |
| **CI comments** | PR comments with fix suggestions | No |
| **Auto-fix** | `/governance fix` | No |
| **LLM advice** | `--advise` — architectural recommendations | No |
| **Module metrics** | Cohesion, public surface, symbol count | No |
| **JSON / HTML output** | Both | Text only |
| **Package install required** | No — scans source directly | Yes — must be importable |
| **Recursive cycle detection** | All directory levels | `acyclic_siblings` contract |
| **Indirect imports** | Direct only | Transitive chains |
| **Speed (Django, 902 files)** | ~1.2s | ~0.1s |
| **Claude Code plugin** | Yes | No |

**Choose import-linter** for transitive import detection or forbidden contracts.
**Choose code-governance** for CI integration, auto-fix, LLM advice, or zero-config setup.

---

<details>
<summary><h3>Governance fix workflow</h3></summary>

Add to `.github/workflows/governance-fix.yml`:

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
