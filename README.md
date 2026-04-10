# paradigm-governance

AST-based governance engine for enforcing module boundaries and architecture rules in Python codebases. Think [import-linter](https://github.com/seddonym/import-linter) but powered by [ast-grep](https://ast-grep.github.io/) for fast, accurate parsing.

Define your modules and allowed dependencies in a `governance.toml` file, then run checks in CI or locally. Detects circular dependencies, undeclared imports across module boundaries, layer violations, and reports module health metrics (cohesion, public surface area).

## Install

```bash
pip install paradigm-governance
```

Or with uv:

```bash
uv add paradigm-governance
```

## Quick Start

### 1. Generate a config from your project

```bash
# Auto-detect modules from folder structure
governance-ast --fix-config --source-root src/

# Or generate with real dependency data pre-populated
governance-ast --generate --source-root src/
```

This creates `governance.toml`:

```toml
[governance]
root = "src"
language = "python"

[[modules]]
name = "api"
path = "api/"
depends_on = ["core", "db"]

[[modules]]
name = "core"
path = "core/"
depends_on = []

[[modules]]
name = "db"
path = "db/"
depends_on = ["core"]

[layers]
order = ["api", "db", "core"]

[rules]
no_cycles = true
enforce_layers = true
enforce_depends_on = true
exclude_test_files = true
```

### 2. Run governance checks

```bash
# Check for violations
governance-ast

# JSON output
governance-ast --format json

# Interactive HTML report
governance-ast --format html > report.html
```

### 3. Discover actual dependencies

```bash
# See what imports what (without enforcement)
governance-ast --discover
```

Output:

```
Module Dependencies — discovered (python)
Modules: 3 | Files scanned: 12

  api (15 symbols)
    → core                 8 imports   (routes.py:3, views.py:1, ...)
    → db                   4 imports   (routes.py:5, views.py:8)

  db (6 symbols)
    → core                 3 imports   (repository.py:1, ...)
```

## Config Reference

### `[governance]`

| Key | Description | Default |
|-----|-------------|---------|
| `root` | Source root relative to config file | `"."` |
| `language` | Language to analyze | `"python"` |
| `package_prefix` | Optional package prefix to strip from imports | — |

### `[[modules]]`

| Key | Description |
|-----|-------------|
| `name` | Module identifier |
| `path` | Directory path relative to root |
| `depends_on` | List of module names this module may import from |
| `layer` | Optional layer assignment (e.g. `"api"`, `"domain"`) |

### `[layers]`

| Key | Description |
|-----|-------------|
| `order` | Ordered list from highest to lowest. Higher layers can depend on lower, not vice versa. |

### `[rules]`

| Key | Description | Default |
|-----|-------------|---------|
| `no_cycles` | Detect circular dependencies between modules | `true` |
| `enforce_depends_on` | Flag imports not listed in `depends_on` | `true` |
| `enforce_layers` | Prevent higher layers from being imported by lower layers | `false` |
| `max_public_surface` | Warn if ratio of externally-used symbols exceeds threshold | — |
| `min_cohesion` | Warn if ratio of internal-to-total imports is below threshold | — |
| `exclude_test_files` | Skip test files during analysis | `true` |
| `exclude_from_cycles` | List of module names to exclude from cycle detection | `[]` |

## CI Usage

### Check only changed files

```bash
governance-ast --diff HEAD~1
```

### Baseline workflow

Accept existing violations and only fail on new ones:

```bash
# Save current state as baseline
governance-ast --save-baseline .governance-baseline.json

# Check against baseline (only new violations fail)
governance-ast --baseline .governance-baseline.json
```

Combined with `--diff`, it auto-loads `.governance-baseline.json` if present:

```bash
governance-ast --diff HEAD~1
```

### GitHub Actions example

```yaml
- name: Check governance
  run: |
    pip install paradigm-governance
    governance-ast --diff origin/main
```

## Agent-Friendly

This tool ships with Claude Code skills in `.claude/skills/` that teach AI agents how to:

- **Use the CLI** — run checks, interpret output, fix violations
- **Generate configs** — brainstorm module boundaries, assign layers, set up rules

See `.claude/skills/governance.md` and `.claude/skills/governance-config.md`.

## License

MIT
