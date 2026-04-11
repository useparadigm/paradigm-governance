# Competitor Analysis — April 2026

## The market

Three tools enforce Python module boundaries. All use the same core approach (AST parsing → dependency graph → rule checking). The difference is in DX, features, and maintenance status.

## tach (tach-org/tach)

**Stats:** 2.7k stars, 1.8M monthly PyPI downloads, written in Rust. Originally by Gauge, **abandoned June 2025**, community fork at tach-org.

**Strengths:**
- Fast (Rust parser)
- Public interface enforcement (restrict which symbols can cross boundaries)
- `visibility` (restrict which modules can import this module)
- `cannot_depend_on` (explicit blocklist)
- Deprecated dependencies (flag and monitor usage)
- Interactive TUI for `tach init`
- VS Code extension

**Weaknesses / user complaints:**
- **Original team stopped maintaining it** — community fork, 45 open issues, no triage
- **Monorepo support broken** — silent failures with uv workspaces, multiple packages (issues #564, #696)
- **Regex vs glob confusion** — #1 usability complaint, patterns silently fail (issue #101)
- **`tach sync` clobbers user config** — overwrites manual settings like `forbid_circular_dependencies` (issue #475, fixed in v0.22)
- **Opaque cycle errors** — no verbose mode, no guidance on resolution (issue #476)
- **50-100+ lines of TOML** for real projects with regex patterns
- **Pytest plugin breaks** with scikit-learn decorators
- **No LLM integration, no PR comments, no auto-fix**

**Real users:** PennyLane (4 layers), PostHog (2 layers, pragmatic workarounds)

**Scaling reality:** Gauge's own blog admits managing all cross-module dependencies is "untenable for projects with 100s of interdependent modules"

**Sources:**
- https://github.com/tach-org/tach/issues/696 (false dependency flagging)
- https://github.com/tach-org/tach/issues/564 (monorepo fails)
- https://github.com/tach-org/tach/issues/101 (regex confusion)
- https://github.com/gauge-sh/tach/issues/476 (opaque cycle errors)
- https://corydonnelly.com/python/first-thoughts-on-tach/ (maintenance stopped)

## import-linter (seddonym/import-linter)

**Stats:** 992 stars, ~50-100 real projects on GitHub, Python-based with grimp (compiled). Actively maintained by David Seddon.

**Strengths:**
- Transitive import detection (A→B→C flagged as A depending on C)
- Multiple contract types (layers, independence, forbidden, acyclic_siblings)
- Recursive cycle detection at every directory level
- Mature, well-documented
- Fast (grimp caching)

**Weaknesses / user complaints:**
- **`src/` layout broken** — pre-commit hooks can't find packages, #1 blocker (issue #214)
- **Monorepo path config missing** — maintainer initially resistant (issue #274)
- **Requires package to be installed and importable** — can't scan source files directly
- **No JSON output**
- **No CI comments, no auto-fix, no LLM advice**
- **No zero-config mode**
- **No diff mode** — every run scans everything
- **No baseline workflow**
- **Custom contracts broken** (issue #45)

**Real users:** OpenEdX, wemake-python-styleguide, Kopf

**Sources:**
- https://github.com/seddonym/import-linter/issues/214 (src/ layout)
- https://github.com/seddonym/import-linter/issues/274 (monorepo)

## code-governance (useparadigm/code-governance)

**Stats:** New, 0.1.0, Python + ast-grep (Rust parser).

**Strengths:**
- Zero-config scan (`--auto` with recursive discovery)
- Auto-generate config from source (`--generate`, `--fix-deps`)
- LLM advice (`--advise` — explains violations, suggests fixes)
- PR comments with violation explanations
- `/governance fix` — auto-apply config updates from PR comments
- Claude Code plugin — interactive setup through conversation
- HTML dependency matrix viewer
- Module metrics (cohesion, public surface)
- Baseline workflow (accept existing violations)
- Diff mode (`--diff HEAD` — only changed files)
- JSON output
- Scans source directly — no package install needed
- No regex in config — TOML with simple lists

**Weaknesses:**
- New, unproven at scale
- Slower than tach (~1.2s vs sub-second on Django)
- Direct imports only — no transitive chain detection
- No public interface enforcement
- No `cannot_depend_on` (whitelist only, no blocklist)
- No VS Code extension
- No `visibility` control

## Positioning opportunity

Their biggest weaknesses are our biggest strengths:

| Pain point | tach | import-linter | code-governance |
|---|---|---|---|
| Config complexity | 50-100 lines, regex | Manual contracts | Auto-generated, simple TOML |
| Error guidance | "cycle detected" (opaque) | Import chain shown | LLM explains why + suggests fix |
| Monorepo support | Broken (silent failures) | Broken (path issues) | Scans source directly |
| Auto-fix | No | No | `/governance fix` on PRs |
| CI integration | Exit code only | Exit code only | PR comments + fix command |
| Maintenance | Abandoned by original team | Active but slow | Active |
| Zero-config | `tach init` (interactive TUI) | No | `--auto` (instant) |
| AI assistance | No | No | `--advise` + Claude Code plugin |

## Key messaging

- "Your codebase already has architecture. We find it, you refine it." (vs tach/import-linter: "define your architecture from scratch")
- "AI tells you what's wrong AND how to fix it." (vs tach: "cycle detected" with no context)
- "One command in CI, fix from the PR comment." (vs both: "exit code 1, figure it out")
- "Works on any Python project. No install, no regex, no TUI." (vs tach: regex patterns, monorepo failures)
