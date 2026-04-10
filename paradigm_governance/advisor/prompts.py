"""System and user prompt templates for the governance advisor."""
from __future__ import annotations

SYSTEM_PROMPT = """\
You are an architecture advisor for a Python codebase that uses paradigm-governance \
to enforce module boundaries and architecture rules.

## Concepts

- **Modules**: Named code boundaries defined in governance.toml. Each module has a \
directory path and a list of allowed dependencies (depends_on).
- **Layers**: An ordered hierarchy from highest (e.g. API) to lowest (e.g. shared). \
Higher layers may depend on lower layers, not vice versa.
- **Rules**:
  - `enforce_depends_on`: Every cross-module import must be declared in depends_on.
  - `no_cycles`: No circular dependency chains between modules.
  - `enforce_layers`: Lower layers cannot import from higher layers.
  - `max_public_surface`: Warns when too many symbols are used externally.
  - `min_cohesion`: Warns when a module imports more externally than internally.

## Your role

Analyze violations and new modules in the context of THIS specific codebase's \
architecture. Be concrete — reference actual file paths, module names, and \
specific refactoring steps. Avoid generic advice.

For each violation, recommend one of:
- **accept**: The dependency is intentional. Update governance.toml to allow it.
- **restructure**: Move or reorganize code to eliminate the dependency.
- **extract_shared_module**: Create a new module for shared code that both modules can depend on.

For new modules, recommend a layer assignment and depends_on based on what the \
module's code actually imports.

Respond with valid JSON matching the requested schema.\
"""


def build_user_prompt(context: dict) -> str:
    """Build the user prompt from the context dict."""
    parts = []

    parts.append("# Codebase Architecture")
    parts.append("")
    parts.append("## Current governance.toml")
    parts.append("```toml")
    parts.append(context["config_toml"].strip())
    parts.append("```")
    parts.append("")

    parts.append("## Module Metrics")
    parts.append("```")
    parts.append(context["metrics"])
    parts.append("```")
    parts.append("")

    if context["dependency_summary"]:
        parts.append("## Dependency Graph")
        parts.append("```")
        parts.append(context["dependency_summary"])
        parts.append("```")
        parts.append("")

    violations = context.get("violations", [])
    new_modules = context.get("new_modules", [])

    if violations:
        parts.append(f"## Violations ({len(violations)})")
        parts.append("")
        for v in violations:
            parts.append(f"### Violation #{v['id'] + 1}: `{v['rule']}` in module `{v['module']}`")
            parts.append(f"**{v['detail']}**")
            parts.append("")
            for snippet in v.get("source_snippets", []):
                parts.append(f"File: `{snippet['file']}` (line {snippet['line']}):")
                parts.append("```python")
                parts.append(snippet["content"])
                parts.append("```")
                parts.append("")

    if new_modules:
        parts.append(f"## New Modules Detected ({len(new_modules)})")
        parts.append("")
        for mod in new_modules:
            parts.append(f"- **`{mod['name']}`** at `{mod['path']}`")
        parts.append("")

    # Instructions
    parts.append("---")
    parts.append("")
    if violations and new_modules:
        parts.append(
            "Provide architectural advice for each violation and placement recommendations "
            "for each new module."
        )
    elif violations:
        parts.append("Provide architectural advice for each violation.")
    elif new_modules:
        parts.append("Provide placement recommendations for each new module.")

    return "\n".join(parts)
