from __future__ import annotations

from code_governance.engine import discover_dependencies, run_governance


def test_graph_edges_on_sample_ts_project(sample_ts_config):
    report = discover_dependencies(sample_ts_config)
    deps = {src: {t.target for t in targets} for src, targets in report.dependencies.items()}

    # core imports db (creates the intentional cycle)
    assert "db" in deps.get("core", set())
    # api imports core, db, utils
    assert "core" in deps.get("api", set())
    assert "db" in deps.get("api", set())
    assert "utils" in deps.get("api", set())
    # db imports core via @/ alias
    assert "core" in deps.get("db", set())


def test_violations_on_sample_ts_project(sample_ts_config):
    report = run_governance(sample_ts_config)
    violation_rules = {v.rule.value for v in report.violations}
    # core has cannot_depend_on=['db'] and imports db → must violate
    assert "enforce_cannot_depend_on" in violation_rules
    # core↔db cycle
    assert "no_cycles" in violation_rules


def test_test_file_is_excluded(sample_ts_config):
    report = run_governance(sample_ts_config)
    # 7 non-test TS files in src/; helpers.test.ts must be excluded
    assert report.total_files_scanned == 7
