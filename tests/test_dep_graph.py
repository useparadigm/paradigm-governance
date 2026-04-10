from code_governance.config import load_config
from code_governance.dep_graph import build_dependency_graph
from code_governance.extractor import extract_directory


def test_build_graph_finds_modules(sample_config):
    config = load_config(sample_config)
    source_root = sample_config.parent
    extractions = extract_directory(source_root, config.language)
    graph = build_dependency_graph(extractions, config)

    # api imports from core, db, utils
    api_deps = graph.get_module_dependencies("api")
    assert "core" in api_deps
    assert "db" in api_deps
    assert "utils" in api_deps

    # db imports from core
    db_deps = graph.get_module_dependencies("db")
    assert "core" in db_deps


def test_build_graph_tracks_symbols(sample_config):
    config = load_config(sample_config)
    source_root = sample_config.parent
    extractions = extract_directory(source_root, config.language)
    graph = build_dependency_graph(extractions, config)

    core_symbols = graph.symbols_per_module.get("core", set())
    assert "User" in core_symbols
    assert "Project" in core_symbols
    assert "validate_email" in core_symbols


def test_build_graph_edge_details(sample_config):
    config = load_config(sample_config)
    source_root = sample_config.parent
    extractions = extract_directory(source_root, config.language)
    graph = build_dependency_graph(extractions, config)

    # Check that edge details contain file-level info
    api_to_core = [e for e in graph.edge_details if e.source_module == "api" and e.target_module == "core"]
    assert len(api_to_core) > 0
    assert any(e.source_file == "api/routes.py" for e in api_to_core)


def test_cycle_detected_in_graph(sample_config):
    """core/service.py imports from db, and db imports from core — cycle."""
    config = load_config(sample_config)
    source_root = sample_config.parent
    extractions = extract_directory(source_root, config.language)
    graph = build_dependency_graph(extractions, config)

    core_deps = graph.get_module_dependencies("core")
    db_deps = graph.get_module_dependencies("db")
    assert "db" in core_deps
    assert "core" in db_deps
