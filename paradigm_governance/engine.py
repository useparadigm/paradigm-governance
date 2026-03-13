from __future__ import annotations

from pathlib import Path

from paradigm_governance.config import load_config
from paradigm_governance.dep_graph import build_dependency_graph
from paradigm_governance.extractor import extract_directory
from paradigm_governance.rules import ALL_RULES, compute_module_metrics
from paradigm_governance.schemas import (
    DependencyTarget,
    DiscoverReport,
    GovernanceConfig,
    GovernanceReport,
    Violation,
)


def run_governance(config_path: str | Path) -> GovernanceReport:
    config_path = Path(config_path)
    config = load_config(config_path)
    repo_root = config_path.parent
    source_root = repo_root / config.root

    if not source_root.exists():
        raise FileNotFoundError(f"Source root not found: {source_root}")

    extractions = extract_directory(source_root, config.language, config.rules.exclude_test_files)

    graph = build_dependency_graph(extractions, config)

    violations: list[Violation] = []
    for rule_fn in ALL_RULES:
        violations.extend(rule_fn(graph, config))

    metrics = compute_module_metrics(graph, config)

    return GovernanceReport(
        config_path=str(config_path),
        language=config.language,
        module_count=len(config.modules),
        total_files_scanned=len(extractions),
        violations=violations,
        metrics=metrics,
    )


def run_governance_diff(config_path: str | Path, git_ref: str = "HEAD") -> GovernanceReport:
    import subprocess

    config_path = Path(config_path)
    config = load_config(config_path)
    repo_root = config_path.parent
    source_root = repo_root / config.root

    if not source_root.exists():
        raise FileNotFoundError(f"Source root not found: {source_root}")

    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", git_ref],
        capture_output=True, text=True, cwd=str(repo_root),
    )
    if result.returncode != 0:
        raise RuntimeError(f"git diff failed: {result.stderr.strip()}")

    changed_files = set()
    root_prefix = config.root.rstrip("/") + "/"
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if line.startswith(root_prefix):
            rel = line[len(root_prefix):]
            changed_files.add(rel)

    all_extractions = extract_directory(source_root, config.language, config.rules.exclude_test_files)

    changed_extractions = [e for e in all_extractions if e.file_path in changed_files]

    graph = build_dependency_graph(all_extractions, config)

    violations: list[Violation] = []
    for rule_fn in ALL_RULES:
        violations.extend(rule_fn(graph, config))

    changed_modules = set()
    for ext in changed_extractions:
        for mod in config.modules:
            mod_path = mod.path.rstrip("/")
            if ext.file_path == mod_path or ext.file_path.startswith(mod_path + "/"):
                changed_modules.add(mod.name)
                break

    filtered = []
    for v in violations:
        if v.module in changed_modules:
            filtered.append(v)
            continue
        if v.evidence:
            relevant = [e for e in v.evidence if e.get("source_file") in changed_files]
            if relevant:
                v = v.model_copy(update={"evidence": relevant})
                filtered.append(v)

    metrics = compute_module_metrics(graph, config)

    return GovernanceReport(
        config_path=str(config_path),
        language=config.language,
        module_count=len(config.modules),
        total_files_scanned=len(changed_extractions),
        violations=filtered,
        metrics=metrics,
    )


def discover_dependencies(config_path: str | Path) -> DiscoverReport:
    from collections import defaultdict

    config_path = Path(config_path)
    config = load_config(config_path)
    repo_root = config_path.parent
    source_root = repo_root / config.root

    if not source_root.exists():
        raise FileNotFoundError(f"Source root not found: {source_root}")

    extractions = extract_directory(source_root, config.language, config.rules.exclude_test_files)
    graph = build_dependency_graph(extractions, config)
    metrics = compute_module_metrics(graph, config)

    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    seen: set[tuple[str, str, str, int]] = set()
    for edge in graph.edge_details:
        key = (edge.source_module, edge.target_module, edge.source_file, edge.line)
        if key in seen:
            continue
        seen.add(key)
        grouped[edge.source_module][edge.target_module].append({
            "file": edge.source_file,
            "line": edge.line,
            "raw_statement": edge.raw_statement,
        })

    dependencies: dict[str, list[DependencyTarget]] = {}
    for src_mod in sorted(grouped):
        targets = []
        for tgt_mod in sorted(grouped[src_mod], key=lambda t: -len(grouped[src_mod][t])):
            files = grouped[src_mod][tgt_mod]
            targets.append(DependencyTarget(
                target=tgt_mod,
                count=len(files),
                files=files,
            ))
        dependencies[src_mod] = targets

    return DiscoverReport(
        config_path=str(config_path),
        language=config.language,
        module_count=len(config.modules),
        total_files_scanned=len(extractions),
        dependencies=dependencies,
        metrics=metrics,
    )


def config_to_toml(config: GovernanceConfig) -> str:
    lines = [
        "[governance]",
        f'root = "{config.root}"',
        f'language = "{config.language.value}"',
        "",
    ]
    for mod in config.modules:
        lines.append("[[modules]]")
        lines.append(f'name = "{mod.name}"')
        lines.append(f'path = "{mod.path}"')
        deps = ", ".join(f'"{d}"' for d in mod.depends_on)
        lines.append(f"depends_on = [{deps}]")
        if mod.layer:
            lines.append(f'layer = "{mod.layer}"')
        lines.append("")
    lines.append("[layers]")
    if config.layers.order:
        order = ", ".join(f'"{o}"' for o in config.layers.order)
        lines.append(f"order = [{order}]")
    else:
        lines.append("order = []")
    lines.append("")
    lines.append("[rules]")
    lines.append(f"no_cycles = {'true' if config.rules.no_cycles else 'false'}")
    lines.append(f"enforce_layers = {'true' if config.rules.enforce_layers else 'false'}")
    lines.append(f"enforce_depends_on = {'true' if config.rules.enforce_depends_on else 'false'}")
    lines.append(f"exclude_test_files = {'true' if config.rules.exclude_test_files else 'false'}")
    if config.rules.exclude_from_cycles:
        excluded = ", ".join(f'"{e}"' for e in config.rules.exclude_from_cycles)
        lines.append(f"exclude_from_cycles = [{excluded}]")
    lines.append("")
    return "\n".join(lines) + "\n"


def generate_config(
    source_root: str | Path,
    language: str = "python",
) -> GovernanceConfig:
    from paradigm_governance.schemas import Language, ModuleConfig

    root = Path(source_root)
    if not root.exists():
        raise FileNotFoundError(f"Source root not found: {root}")

    lang = Language(language)
    modules: list[ModuleConfig] = []

    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name.startswith("_"):
            continue
        if child.name in ("node_modules", "__pycache__", ".git", "venv", ".venv"):
            continue

        modules.append(ModuleConfig(
            name=child.name,
            path=child.name + "/",
            depends_on=[],
        ))

    return GovernanceConfig(
        root=".",
        language=lang,
        modules=modules,
    )


def generate_config_with_ai(
    source_root: str | Path,
    language: str = "python",
    config_path: str | Path = "governance.toml",
) -> GovernanceConfig:
    import tempfile

    from paradigm_governance.ai_config_generator import collect_repo_tree, enrich_config_via_ai

    source_root = Path(source_root).resolve()
    base_config = generate_config(source_root, language)
    base_toml = config_to_toml(base_config)
    tree = collect_repo_tree(source_root, language)
    enriched = enrich_config_via_ai(base_toml, tree)

    # Write temp config in source_root's parent so root="." resolves correctly
    tmp_path = source_root.parent / f".governance-tmp-{id(enriched)}.toml"
    enriched_for_disk = enriched.model_copy(update={"root": source_root.name})
    tmp_path.write_text(config_to_toml(enriched_for_disk))

    try:
        final = populate_dependencies(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    # Reset root back to "." for the output config
    final.root = "."
    return final


def populate_dependencies(config_path: str | Path) -> GovernanceConfig:
    config_path = Path(config_path)
    config = load_config(config_path)
    repo_root = config_path.parent
    source_root = repo_root / config.root

    if not source_root.exists():
        raise FileNotFoundError(f"Source root not found: {source_root}")

    extractions = extract_directory(source_root, config.language, config.rules.exclude_test_files)
    graph = build_dependency_graph(extractions, config)

    module_names = {mod.name for mod in config.modules}
    for mod in config.modules:
        deps = sorted(
            t for t in graph.module_edges.get(mod.name, {})
            if t in module_names and t != mod.name
        )
        mod.depends_on = deps

    return config
