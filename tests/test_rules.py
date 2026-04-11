from code_governance.config import load_config
from code_governance.dep_graph import build_dependency_graph
from code_governance.extractor import extract_directory
from code_governance.rules import (
    check_enforce_depends_on,
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


def test_enforce_depends_on_detects_undeclared(sample_config):
    graph, config = _build_graph(sample_config)
    violations = check_enforce_depends_on(graph, config)
    # core depends_on is empty but core/service.py imports from db
    assert len(violations) > 0
    undeclared = [v for v in violations if v.module == "core"]
    assert len(undeclared) > 0
    assert "db" in undeclared[0].detail


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
