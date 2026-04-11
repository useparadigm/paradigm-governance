from code_governance.config import load_config
from code_governance.dep_graph import build_dependency_graph
from code_governance.extractor import extract_directory
from code_governance.rules import (
    check_enforce_cannot_depend_on,
    check_enforce_layers,
    check_min_cohesion,
    check_max_public_surface,
    check_no_cycles,
    compute_module_metrics,
)
from code_governance.schemas import RuleKind


def _build_graph(sample_config):
    config = load_config(sample_config)
    source_root = sample_config.parent
    extractions = extract_directory(source_root, config.language)
    graph = build_dependency_graph(extractions, config)
    return graph, config


def test_no_cycles_detects_cycle(sample_config):
    graph, config = _build_graph(sample_config)
    violations = check_no_cycles(graph, config)
    assert len(violations) > 0
    assert all(v.rule == RuleKind.NO_CYCLES for v in violations)
    cycle_details = " ".join(v.detail for v in violations)
    assert "core" in cycle_details
    assert "db" in cycle_details


def test_enforce_cannot_depend_on_detects_forbidden(sample_config):
    graph, config = _build_graph(sample_config)
    violations = check_enforce_cannot_depend_on(graph, config)
    # core cannot_depend_on = ["db"] but core/service.py imports from db
    assert len(violations) > 0
    forbidden = [v for v in violations if v.module == "core"]
    assert len(forbidden) > 0
    assert "db" in forbidden[0].detail


def test_enforce_layers_detects_violation(sample_config):
    """Layer order: api(0) > db(1) > core(2) > utils(3).
    db(rank 1) imports core(rank 2) — dep_rank > src_rank — layer violation.
    """
    graph, config = _build_graph(sample_config)
    violations = check_enforce_layers(graph, config)
    # db -> core is a layer violation (db is higher than core)
    layer_violations = [v for v in violations if v.module == "db"]
    assert len(layer_violations) > 0
    assert "core" in layer_violations[0].detail


def test_compute_metrics(sample_config):
    graph, config = _build_graph(sample_config)
    metrics = compute_module_metrics(graph, config)
    assert len(metrics) == 4
    by_name = {m.name: m for m in metrics}
    assert by_name["core"].total_symbols > 0
    assert by_name["utils"].total_symbols > 0


def test_max_public_surface(sample_config):
    graph, config = _build_graph(sample_config)
    # Set a very low threshold to trigger the rule
    config.rules.max_public_surface = 0.01
    violations = check_max_public_surface(graph, config)
    assert len(violations) > 0
    assert all(v.rule == RuleKind.MAX_PUBLIC_SURFACE for v in violations)


def test_min_cohesion(sample_config):
    graph, config = _build_graph(sample_config)
    # Set a very high threshold to trigger the rule
    config.rules.min_cohesion = 0.99
    violations = check_min_cohesion(graph, config)
    assert len(violations) > 0
    assert all(v.rule == RuleKind.MIN_COHESION for v in violations)


# ── Transitive dependency tests ──


def test_transitive_cannot_depend_on(transitive_config):
    """api.cannot_depend_on = ["db"], but api → service → db should be caught."""
    graph, config = _build_graph(transitive_config)
    # transitive is already True in the fixture config
    violations = check_enforce_cannot_depend_on(graph, config)
    transitive_v = [v for v in violations if "transitive" in v.detail.lower()]
    assert len(transitive_v) >= 1
    v = transitive_v[0]
    assert v.module == "api"
    assert "db" in v.detail
    assert "api → service → db" in v.detail


def test_transitive_layer_violation(transitive_config):
    """Layer order ["api", "service", "db", "utils"]: modules can only import
    from layers earlier in the list (lower index). api → service is a direct
    violation. Transitively, api → service → db reaches db (index 2), which
    should be flagged as a transitive layer violation (not just direct)."""
    graph, config = _build_graph(transitive_config)
    violations = check_enforce_layers(graph, config)
    transitive_v = [v for v in violations if "transitive" in v.detail.lower()]
    # api transitively reaches db and utils (both higher index than api)
    # but api → service is already a direct violation, so transitive only reports
    # the ones not caught directly: api → db (via service) and api → utils (via service → db)
    assert len(transitive_v) >= 1
    # Verify chain is shown
    assert any("→" in v.detail for v in transitive_v)


def test_transitive_off_by_default(transitive_config):
    """With transitive=false, only direct violations are reported."""
    graph, config = _build_graph(transitive_config)
    config.rules.transitive = False
    violations = check_enforce_cannot_depend_on(graph, config)
    # api does not directly import db, so no violation
    api_violations = [v for v in violations if v.module == "api"]
    assert len(api_violations) == 0


def test_transitive_chain_in_detail(transitive_config):
    """Violation detail must include the full chain."""
    graph, config = _build_graph(transitive_config)
    violations = check_enforce_cannot_depend_on(graph, config)
    transitive_v = [v for v in violations if "transitive" in v.detail.lower()]
    assert len(transitive_v) >= 1
    # Check chain format: "api → service → db"
    assert "→" in transitive_v[0].detail
    assert transitive_v[0].evidence  # should have evidence for each hop


def test_transitive_no_infinite_loop_on_cycles(sample_config):
    """Ensure transitive BFS doesn't hang on the core ↔ db cycle."""
    graph, config = _build_graph(sample_config)
    config.rules.transitive = True
    # Should complete without hanging
    violations = check_enforce_cannot_depend_on(graph, config)
    # core.cannot_depend_on = ["db"] — direct violation exists, no extra transitive
    core_v = [v for v in violations if v.module == "core"]
    assert len(core_v) >= 1
