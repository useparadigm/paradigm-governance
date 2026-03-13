from __future__ import annotations

from dataclasses import asdict

from paradigm_governance.dep_graph import DependencyGraph
from paradigm_governance.schemas import (
    EdgeDetail,
    GovernanceConfig,
    ModuleMetrics,
    RuleKind,
    Severity,
    Violation,
)


def _evidence_for_edge(edge_details: list[EdgeDetail], src: str, tgt: str) -> list[dict]:
    seen: set[tuple[str, int]] = set()
    results: list[dict] = []
    for e in edge_details:
        if e.source_module != src or e.target_module != tgt:
            continue
        key = (e.source_file, e.line)
        if key in seen:
            continue
        seen.add(key)
        results.append(asdict(e))
    return results


def check_no_cycles(graph: DependencyGraph, config: GovernanceConfig) -> list[Violation]:
    if not config.rules.no_cycles:
        return []

    excluded = set(config.rules.exclude_from_cycles)
    module_names = {m.name for m in config.modules} - excluded
    adjacency: dict[str, set[str]] = {}
    for mod in module_names:
        adjacency[mod] = (graph.get_module_dependencies(mod) & module_names) - excluded

    cycles = _find_cycles(adjacency)

    allowed: dict[str, set[str]] = {}
    if config.rules.enforce_depends_on:
        for mod in config.modules:
            allowed[mod.name] = set(mod.depends_on)

    unique_cycles: list[list[str]] = []
    seen_cycles: set[frozenset[str]] = set()
    for cycle in cycles:
        key = frozenset(cycle)
        if key in seen_cycles:
            continue
        seen_cycles.add(key)
        unique_cycles.append(cycle)

    unique_cycles.sort(key=len)

    simple_node_sets = [frozenset(c) for c in unique_cycles if len(c) == 2]

    violations: list[Violation] = []
    for cycle in unique_cycles:
        if len(cycle) > 2:
            is_superset = any(s.issubset(frozenset(cycle)) for s in simple_node_sets)
            if is_superset:
                continue

        if config.rules.enforce_depends_on and allowed:
            edges = [(cycle[i], cycle[(i + 1) % len(cycle)]) for i in range(len(cycle))]
            has_disallowed = any(
                tgt not in allowed.get(src, set()) for src, tgt in edges
            )
            if has_disallowed:
                continue

        cycle_str = " -> ".join(cycle + [cycle[0]])
        evidence: list[dict] = []
        for i in range(len(cycle)):
            src = cycle[i]
            tgt = cycle[(i + 1) % len(cycle)]
            evidence.extend(_evidence_for_edge(graph.edge_details, src, tgt))
        violations.append(Violation(
            rule=RuleKind.NO_CYCLES,
            module=cycle[0],
            detail=f"Circular dependency: {cycle_str}",
            evidence=evidence,
        ))

    return violations


def check_enforce_layers(graph: DependencyGraph, config: GovernanceConfig) -> list[Violation]:
    if not config.rules.enforce_layers or not config.layers.order:
        return []

    layer_rank = {layer: i for i, layer in enumerate(config.layers.order)}
    module_layer = {m.name: m.layer for m in config.modules if m.layer}

    violations: list[Violation] = []
    for src_mod, deps in graph.module_edges.items():
        src_layer = module_layer.get(src_mod)
        if not src_layer or src_layer not in layer_rank:
            continue
        src_rank = layer_rank[src_layer]

        for dep_mod in deps:
            dep_layer = module_layer.get(dep_mod)
            if not dep_layer or dep_layer not in layer_rank:
                continue
            dep_rank = layer_rank[dep_layer]

            if dep_rank > src_rank:
                evidence = _evidence_for_edge(graph.edge_details, src_mod, dep_mod)
                violations.append(Violation(
                    rule=RuleKind.ENFORCE_LAYERS,
                    module=src_mod,
                    detail=f"Layer violation: '{src_mod}' ({src_layer}) imports '{dep_mod}' ({dep_layer})",
                    evidence=evidence,
                ))

    return violations


def check_enforce_depends_on(graph: DependencyGraph, config: GovernanceConfig) -> list[Violation]:
    if not config.rules.enforce_depends_on:
        return []

    allowed: dict[str, set[str]] = {}
    for mod in config.modules:
        allowed[mod.name] = set(mod.depends_on)

    violations: list[Violation] = []
    for src_mod, deps in graph.module_edges.items():
        if src_mod not in allowed:
            continue
        for dep_mod in deps:
            if dep_mod not in allowed.get(src_mod, set()):
                evidence = _evidence_for_edge(graph.edge_details, src_mod, dep_mod)
                violations.append(Violation(
                    rule=RuleKind.ENFORCE_DEPENDS_ON,
                    module=src_mod,
                    detail=f"Undeclared dependency: '{src_mod}' imports '{dep_mod}' (allowed: {sorted(allowed.get(src_mod, set()))})",
                    evidence=evidence,
                ))

    return violations


def check_max_public_surface(graph: DependencyGraph, config: GovernanceConfig) -> list[Violation]:
    threshold = config.rules.max_public_surface
    if threshold is None:
        return []

    violations: list[Violation] = []
    for mod in config.modules:
        total = len(graph.symbols_per_module.get(mod.name, set()))
        external = len(graph.externally_used_symbols.get(mod.name, set()))
        if total == 0:
            continue
        ratio = external / total
        if ratio > threshold:
            violations.append(Violation(
                rule=RuleKind.MAX_PUBLIC_SURFACE,
                module=mod.name,
                detail=f"Public surface {ratio:.2f} exceeds threshold {threshold} ({external}/{total} symbols used externally)",
                severity=Severity.WARNING,
            ))

    return violations


def check_min_cohesion(graph: DependencyGraph, config: GovernanceConfig) -> list[Violation]:
    threshold = config.rules.min_cohesion
    if threshold is None:
        return []

    violations: list[Violation] = []
    for mod in config.modules:
        internal = graph.module_internal_edges.get(mod.name, 0)
        external = graph.module_external_edges.get(mod.name, 0)
        total = internal + external
        if total == 0:
            continue
        ratio = internal / total
        if ratio < threshold:
            violations.append(Violation(
                rule=RuleKind.MIN_COHESION,
                module=mod.name,
                detail=f"Cohesion {ratio:.2f} below threshold {threshold} ({internal} internal / {total} total edges)",
                severity=Severity.WARNING,
            ))

    return violations


def compute_module_metrics(graph: DependencyGraph, config: GovernanceConfig) -> list[ModuleMetrics]:
    metrics: list[ModuleMetrics] = []
    for mod in config.modules:
        total_symbols = len(graph.symbols_per_module.get(mod.name, set()))
        ext_symbols = len(graph.externally_used_symbols.get(mod.name, set()))
        internal = graph.module_internal_edges.get(mod.name, 0)
        external = graph.module_external_edges.get(mod.name, 0)
        total_edges = internal + external

        metrics.append(ModuleMetrics(
            name=mod.name,
            total_symbols=total_symbols,
            externally_used_symbols=ext_symbols,
            internal_edges=internal,
            external_edges=external,
            public_surface_ratio=round(ext_symbols / total_symbols, 4) if total_symbols > 0 else None,
            cohesion_ratio=round(internal / total_edges, 4) if total_edges > 0 else None,
        ))
    return metrics


ALL_RULES = [
    check_no_cycles,
    check_enforce_layers,
    check_enforce_depends_on,
    check_max_public_surface,
    check_min_cohesion,
]


def _find_cycles(adjacency: dict[str, set[str]]) -> list[list[str]]:
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in adjacency}
    path: list[str] = []
    cycles: list[list[str]] = []

    def dfs(node: str):
        color[node] = GRAY
        path.append(node)
        for neighbor in adjacency.get(node, set()):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                idx = path.index(neighbor)
                cycles.append(path[idx:])
            elif color[neighbor] == WHITE:
                dfs(neighbor)
        path.pop()
        color[node] = BLACK

    for node in adjacency:
        if color[node] == WHITE:
            dfs(node)

    return cycles
