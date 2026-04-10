"""Generate CI-friendly markdown reports with violation explanations and config suggestions."""
from __future__ import annotations

import json
from pathlib import Path

from paradigm_governance.config import load_config
from paradigm_governance.engine import (
    config_to_toml,
    discover_dependencies,
    generate_config,
    run_governance,
)
from paradigm_governance.schemas import GovernanceConfig, RuleKind, Violation

RULE_EXPLANATIONS: dict[RuleKind, dict[str, str]] = {
    RuleKind.ENFORCE_DEPENDS_ON: {
        "what": "This module imports from another module that isn't listed in its `depends_on`.",
        "why": "Undeclared dependencies make the architecture hard to reason about — any module can quietly couple to any other.",
        "fix_declared": "Add `\"{target}\"` to `{module}`'s `depends_on` in `governance.toml`.",
        "fix_restructure": "Move the shared code to a module both can depend on, or remove the import.",
    },
    RuleKind.NO_CYCLES: {
        "what": "These modules form a circular dependency chain.",
        "why": "Cycles make modules impossible to use or test independently. Changes in one ripple unpredictably through the others.",
        "fix": "Break the cycle by extracting shared types into a separate module, using dependency injection, or merging tightly-coupled modules.",
    },
    RuleKind.ENFORCE_LAYERS: {
        "what": "A higher-level layer is being imported by a lower-level one.",
        "why": "Layer violations invert the dependency direction — infrastructure should not drive the API layer.",
        "fix": "Restructure so dependencies flow downward: high layers depend on low layers, not vice versa.",
    },
    RuleKind.MAX_PUBLIC_SURFACE: {
        "what": "Too many of this module's symbols are used by other modules.",
        "why": "A large public surface means the module is hard to change without breaking dependents.",
        "fix": "Reduce exposure by making internal helpers private (prefix with `_`) or split the module into focused sub-modules.",
    },
    RuleKind.MIN_COHESION: {
        "what": "This module imports more from outside than from within itself.",
        "why": "Low cohesion suggests the module is a grab-bag of unrelated code rather than a focused unit.",
        "fix": "Move tightly-coupled code into the same module, or split into smaller, focused modules.",
    },
}


def _explain_violation(v: Violation) -> str:
    """Generate a markdown explanation for a single violation."""
    info = RULE_EXPLANATIONS.get(v.rule, {})
    lines = []

    severity_icon = "🔴" if v.severity.value == "error" else "🟡"
    lines.append(f"### {severity_icon} `{v.rule.value}` — {v.module}")
    lines.append("")
    lines.append(f"**{v.detail}**")
    lines.append("")

    if info.get("what"):
        lines.append(f"**What:** {info['what']}")
    if info.get("why"):
        lines.append(f"**Why it matters:** {info['why']}")
    lines.append("")

    # Evidence
    if v.evidence:
        lines.append("<details>")
        lines.append(f"<summary>Evidence ({len(v.evidence)} import{'s' if len(v.evidence) != 1 else ''})</summary>")
        lines.append("")
        lines.append("```")
        for e in v.evidence[:10]:
            sf = e.get("source_file", "")
            ln = e.get("line", "")
            raw = e.get("raw_statement", "").strip()
            if len(raw) > 100:
                raw = raw[:97] + "..."
            lines.append(f"{sf}:{ln}  {raw}")
        if len(v.evidence) > 10:
            lines.append(f"... and {len(v.evidence) - 10} more")
        lines.append("```")
        lines.append("</details>")
        lines.append("")

    # Fix suggestions
    if v.rule == RuleKind.ENFORCE_DEPENDS_ON:
        target = ""
        if "imports '" in v.detail:
            target = v.detail.split("imports '")[1].split("'")[0]

        lines.append("**How to fix:**")
        if target:
            fix_config = info.get("fix_declared", "").format(target=target, module=v.module)
            lines.append(f"- ✅ If intentional: {fix_config}")
        lines.append(f"- 🔧 If not: {info.get('fix_restructure', '')}")
    elif info.get("fix"):
        lines.append(f"**How to fix:** {info['fix']}")

    lines.append("")
    return "\n".join(lines)


def _find_new_modules(
    config: GovernanceConfig,
    source_root: Path,
) -> list[dict[str, str]]:
    """Find directories with source files that aren't in the config."""
    discovered = generate_config(str(source_root), "python")
    existing_paths = {m.path.rstrip("/") for m in config.modules}
    # Also match catch-all
    existing_names = {m.name for m in config.modules}

    new_modules = []
    for mod in discovered.modules:
        mod_path = mod.path.rstrip("/")
        if mod_path not in existing_paths and mod.name not in existing_names and mod_path != ".":
            new_modules.append({"name": mod.name, "path": mod.path})
    return new_modules


def _suggest_config_update(
    config: GovernanceConfig,
    new_modules: list[dict[str, str]],
    source_root: Path,
) -> str:
    """Generate an updated governance.toml with new modules added."""
    from paradigm_governance.schemas import ModuleConfig

    updated = config.model_copy(deep=True)
    for mod in new_modules:
        updated.modules.append(ModuleConfig(
            name=mod["name"],
            path=mod["path"],
            depends_on=[],
        ))

    return config_to_toml(updated)


def generate_ci_report(
    config_path: str | Path,
    advise: bool = False,
) -> dict:
    """Generate a full CI report with violations, new modules, and suggestions.

    Returns a dict with:
        - markdown: str — the full markdown report
        - violations: list — violation objects
        - new_modules: list — new module dicts
        - updated_config: str | None — updated governance.toml content if new modules found
        - passed: bool
    """
    config_path = Path(config_path)
    config = load_config(config_path)
    source_root = config_path.parent / config.root

    report = run_governance(config_path)
    new_modules = _find_new_modules(config, source_root)

    lines = []
    lines.append("## Governance Report")
    lines.append("")
    lines.append(f"**Modules:** {report.module_count} | **Files scanned:** {report.total_files_scanned}")
    lines.append("")

    # Violations
    if report.violations:
        lines.append(f"### ❌ {len(report.violations)} violation{'s' if len(report.violations) != 1 else ''} found")
        lines.append("")
        for v in report.violations:
            lines.append(_explain_violation(v))
    else:
        lines.append("### ✅ No violations")
        lines.append("")

    # New modules
    updated_config = None
    if new_modules:
        lines.append("---")
        lines.append("")
        lines.append(f"### 📦 {len(new_modules)} new module{'s' if len(new_modules) != 1 else ''} detected")
        lines.append("")
        lines.append("The following directories contain Python files but aren't in `governance.toml`:")
        lines.append("")
        for mod in new_modules:
            lines.append(f"- **`{mod['name']}`** (`{mod['path']}`)")
        lines.append("")

        updated_config = _suggest_config_update(config, new_modules, source_root)
        lines.append("Add them to your config:")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>Suggested governance.toml update</summary>")
        lines.append("")
        lines.append("```toml")
        # Only show the new module blocks
        for mod in new_modules:
            lines.append(f'[[modules]]')
            lines.append(f'name = "{mod["name"]}"')
            lines.append(f'path = "{mod["path"]}"')
            lines.append(f'depends_on = []')
            lines.append("")
        lines.append("```")
        lines.append("</details>")
        lines.append("")
        lines.append("> 💡 Run `governance-ast --fix-deps` after adding modules to auto-populate `depends_on` from actual imports.")
        lines.append("")

    # Metrics summary
    if report.metrics:
        lines.append("---")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>Module metrics</summary>")
        lines.append("")
        lines.append("| Module | Symbols | Cohesion | Surface | Internal | External |")
        lines.append("|--------|---------|----------|---------|----------|----------|")
        for m in report.metrics:
            cohesion = f"{m.cohesion_ratio:.2f}" if m.cohesion_ratio is not None else "—"
            surface = f"{m.public_surface_ratio:.2f}" if m.public_surface_ratio is not None else "—"
            lines.append(f"| {m.name} | {m.total_symbols} | {cohesion} | {surface} | {m.internal_edges} | {m.external_edges} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # LLM advice
    advice_data = None
    if advise and (report.violations or new_modules):
        try:
            from paradigm_governance.advisor import generate_advice

            advice = generate_advice(config_path, governance_report=report, new_modules=new_modules)
            if advice:
                lines.append("---")
                lines.append("")
                lines.append(advice.to_markdown())
                advice_data = advice.model_dump()
        except Exception as e:
            lines.append("---")
            lines.append("")
            lines.append(f"## AI Architecture Advice\n\n⚠️ LLM advice unavailable: {e}")

    markdown = "\n".join(lines)

    return {
        "markdown": markdown,
        "violations": [v.model_dump() for v in report.violations],
        "new_modules": new_modules,
        "updated_config": updated_config,
        "advice": advice_data,
        "passed": report.passed and len(new_modules) == 0,
    }


def main():
    """CLI entrypoint for ci-report."""
    import argparse

    parser = argparse.ArgumentParser(prog="governance-ci-report")
    parser.add_argument("--config", "-c", default="governance.toml")
    parser.add_argument("--output-markdown", help="Write markdown report to file")
    parser.add_argument("--output-config", help="Write updated governance.toml (if new modules found)")
    parser.add_argument("--json", action="store_true", help="Output full report as JSON")
    parser.add_argument("--advise", action="store_true", help="Use LLM to generate architectural advice")
    args = parser.parse_args()

    result = generate_ci_report(args.config, advise=args.advise)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["markdown"])

    if args.output_markdown:
        Path(args.output_markdown).write_text(result["markdown"])

    if args.output_config and result["updated_config"]:
        Path(args.output_config).write_text(result["updated_config"])

    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
