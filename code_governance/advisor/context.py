"""Build LLM context from governance reports and source files."""
from __future__ import annotations

from pathlib import Path

from code_governance.engine import config_to_toml, generate_config
from code_governance.schemas import (
    DiscoverReport,
    GovernanceConfig,
    GovernanceReport,
    Violation,
)

SOURCE_WINDOW = 15  # lines above and below violation
MAX_SOURCE_CHARS = 32_000


def build_context(
    config: GovernanceConfig,
    config_path: Path,
    governance_report: GovernanceReport,
    discover_report: DiscoverReport | None = None,
) -> dict:
    """Build a structured context dict for the LLM prompt."""
    source_root = config_path.parent / config.root

    return {
        "config_toml": config_to_toml(config),
        "violations": _build_violation_contexts(
            governance_report.violations, source_root
        ),
        "new_modules": _find_new_modules(config, source_root),
        "metrics": _build_metrics_summary(governance_report),
        "dependency_summary": _build_dependency_summary(discover_report),
    }


def _build_violation_contexts(
    violations: list[Violation],
    source_root: Path,
) -> list[dict]:
    """Build violation context with source code snippets."""
    results = []
    total_chars = 0
    seen_files: dict[str, str] = {}

    for i, v in enumerate(violations):
        ctx: dict = {
            "id": i,
            "rule": v.rule.value,
            "module": v.module,
            "detail": v.detail,
            "severity": v.severity.value,
            "source_snippets": [],
        }

        for e in v.evidence[:5]:
            source_file = e.get("source_file", "")
            line = e.get("line", 0)
            if not source_file or not line:
                continue

            if total_chars >= MAX_SOURCE_CHARS:
                break

            snippet = _get_source_snippet(source_root, source_file, line, seen_files)
            if snippet:
                total_chars += len(snippet["content"])
                ctx["source_snippets"].append(snippet)

        results.append(ctx)

    return results


def _get_source_snippet(
    source_root: Path,
    file_path: str,
    line: int,
    cache: dict[str, str],
) -> dict | None:
    """Read a window of source around a specific line."""
    if file_path in cache:
        content = cache[file_path]
    else:
        full_path = source_root / file_path
        if not full_path.exists():
            return None
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            cache[file_path] = content
        except Exception:
            return None

    lines = content.splitlines()
    start = max(0, line - SOURCE_WINDOW - 1)
    end = min(len(lines), line + SOURCE_WINDOW)
    window = lines[start:end]

    numbered = []
    for i, l in enumerate(window, start=start + 1):
        marker = ">>>" if i == line else "   "
        numbered.append(f"{marker} {i:4d} | {l}")

    snippet_content = "\n".join(numbered)
    return {
        "file": file_path,
        "line": line,
        "content": snippet_content,
    }


def _find_new_modules(
    config: GovernanceConfig,
    source_root: Path,
) -> list[dict[str, str]]:
    """Find directories with source files not in the config."""
    discovered = generate_config(str(source_root), "python")
    existing_paths = {m.path.rstrip("/") for m in config.modules}
    existing_names = {m.name for m in config.modules}

    new_modules = []
    for mod in discovered.modules:
        mod_path = mod.path.rstrip("/")
        if mod_path not in existing_paths and mod.name not in existing_names and mod_path != ".":
            new_modules.append({"name": mod.name, "path": mod.path})
    return new_modules


def _build_metrics_summary(report: GovernanceReport) -> str:
    """Build a text table of module metrics."""
    if not report.metrics:
        return "No metrics available."

    lines = ["Module | Symbols | Cohesion | Surface | In-edges | Out-edges"]
    lines.append("-------|---------|----------|---------|----------|----------")
    for m in report.metrics:
        cohesion = f"{m.cohesion_ratio:.2f}" if m.cohesion_ratio is not None else "—"
        surface = f"{m.public_surface_ratio:.2f}" if m.public_surface_ratio is not None else "—"
        lines.append(
            f"{m.name} | {m.total_symbols} | {cohesion} | {surface} | {m.internal_edges} | {m.external_edges}"
        )
    return "\n".join(lines)


def _build_dependency_summary(report: DiscoverReport | None) -> str:
    """Build a condensed text summary of the dependency graph."""
    if not report or not report.dependencies:
        return "No dependency data available."

    lines = []
    for src, targets in sorted(report.dependencies.items()):
        target_strs = []
        for t in sorted(targets, key=lambda x: -x.count):
            target_strs.append(f"{t.target}({t.count})")
        lines.append(f"{src} → {', '.join(target_strs)}")
    return "\n".join(lines)
