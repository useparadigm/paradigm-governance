from code_governance.engine import (
    discover_dependencies,
    generate_config,
    run_governance,
)


def test_run_governance(sample_config):
    report = run_governance(sample_config)
    assert report.language.value == "python"
    assert report.module_count == 4
    assert report.total_files_scanned > 0
    # Should have violations (cycle + undeclared dep)
    assert len(report.violations) > 0
    assert not report.passed


def test_discover_dependencies(sample_config):
    report = discover_dependencies(sample_config)
    assert report.module_count == 4
    assert "api" in report.dependencies
    api_targets = {t.target for t in report.dependencies["api"]}
    assert "core" in api_targets
    assert "db" in api_targets


def test_generate_config(sample_project):
    config = generate_config(sample_project, "python")
    module_names = {m.name for m in config.modules}
    assert "core" in module_names
    assert "db" in module_names
    assert "api" in module_names
    assert "utils" in module_names


def test_run_governance_has_metrics(sample_config):
    report = run_governance(sample_config)
    assert len(report.metrics) == 4
    core_metrics = next(m for m in report.metrics if m.name == "core")
    assert core_metrics.total_symbols > 0
