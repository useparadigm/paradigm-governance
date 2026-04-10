# Skill: Using paradigm-governance

Use this skill when asked to check architecture rules, find dependency violations, analyze module boundaries, or run governance checks on a Python codebase.

## Prerequisites

The project needs `paradigm-governance` installed and a `governance.toml` config file.

```bash
# Install if not present
uv add paradigm-governance
# or: pip install paradigm-governance
```

## Running Checks

### Full check
```bash
governance-ast --config governance.toml
```

Exit code 0 = passed, 1 = violations found.

### Check only changed files (CI-friendly)
```bash
governance-ast --diff HEAD
governance-ast --diff origin/main
```

### JSON output (for programmatic use)
```bash
governance-ast --format json
```

### HTML report
```bash
governance-ast --format html > report.html
```

### Discover dependencies (no enforcement)
```bash
governance-ast --discover
governance-ast --discover --format json
```

## Understanding Output

### Violations
Each violation shows:
- **Rule**: which rule was broken (`no_cycles`, `enforce_depends_on`, `enforce_layers`, `max_public_surface`, `min_cohesion`)
- **Module**: the offending module
- **Detail**: human-readable description
- **Evidence**: file:line showing the exact import

### Metrics
- **symbols**: total classes + functions in the module
- **cohesion**: ratio of internal imports to total imports (higher = more self-contained)
- **surface**: ratio of externally-used symbols to total symbols (lower = better encapsulation)
- **edges(in=N, out=M)**: internal vs external import count

## Fixing Violations

### `enforce_depends_on` violations
Module X imports from module Y but Y is not in X's `depends_on` list.

Options:
1. **Add the dependency**: add Y to X's `depends_on` in governance.toml
2. **Move the code**: relocate the shared code to a common module both can depend on
3. **Remove the import**: refactor to eliminate the cross-boundary import

### `no_cycles` violations
Modules form a circular dependency chain (A -> B -> A).

Options:
1. **Extract shared code**: move shared types/interfaces into a separate module
2. **Invert the dependency**: use dependency injection or callbacks
3. **Merge modules**: if they're tightly coupled, they might be one module

### `enforce_layers` violations
A lower layer imports from a higher layer.

Fix: restructure so dependencies flow downward (high layers depend on low layers, not vice versa).

### `max_public_surface` / `min_cohesion` warnings
Module has poor encapsulation or is too fragmented.

Options:
1. Split large modules into focused sub-modules
2. Use `__init__.py` to control what's exported
3. Move tightly-coupled code into the same module

## Baseline Workflow

When adopting governance on an existing codebase:

```bash
# 1. Save current violations as accepted
governance-ast --save-baseline .governance-baseline.json

# 2. Commit the baseline
git add .governance-baseline.json

# 3. Future checks only fail on NEW violations
governance-ast --baseline .governance-baseline.json
```

## Auto-populating dependencies

If you have a config with modules but empty `depends_on`, auto-populate from actual imports:

```bash
governance-ast --fix-deps
```

This rewrites `governance.toml` in place with real dependency data.
