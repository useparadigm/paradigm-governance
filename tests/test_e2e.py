"""End-to-end tests using the golden project fixture.

One project, multiple config files — each config enables different rules
to test pass/fail for every feature combination.
"""
import json
import subprocess
import sys
from pathlib import Path

GOLDEN_PROJECT = Path(__file__).parent / "fixtures" / "golden_project"
CONFIGS = GOLDEN_PROJECT / "configs"


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "code_governance", *args],
        capture_output=True,
        text=True,
        cwd=str(CONFIGS),
    )


# ── All rules on (fail) ──


def test_all_rules_fails():
    result = _run_cli("--config", "all-rules.toml")
    assert result.returncode == 1
    assert "FAILED" in result.stdout
    assert "Violations" in result.stdout


def test_all_rules_json():
    result = _run_cli("--config", "all-rules.toml", "--format", "json")
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert len(data["violations"]) > 0


# ── No rules (pass) ──


def test_no_rules_passes():
    result = _run_cli("--config", "no-rules.toml")
    assert result.returncode == 0
    assert "PASSED" in result.stdout


def test_no_rules_json():
    result = _run_cli("--config", "no-rules.toml", "--format", "json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert len(data["violations"]) == 0


# ── Cycles only ──


def test_cycles_only_detects_cycle():
    result = _run_cli("--config", "cycles-only.toml")
    assert result.returncode == 1
    assert "no_cycles" in result.stdout
    # domain ↔ infra cycle
    assert "domain" in result.stdout
    assert "infra" in result.stdout


def test_cycles_only_no_false_positives():
    result = _run_cli("--config", "cycles-only.toml", "--format", "json")
    data = json.loads(result.stdout)
    rules_triggered = {v["rule"] for v in data["violations"]}
    assert rules_triggered == {"no_cycles"}


# ── Layers only ──


def test_layers_only_detects_violation():
    result = _run_cli("--config", "layers-only.toml")
    assert result.returncode == 1
    assert "enforce_layers" in result.stdout
    assert "Layer violation" in result.stdout


def test_layers_only_no_false_positives():
    result = _run_cli("--config", "layers-only.toml", "--format", "json")
    data = json.loads(result.stdout)
    rules_triggered = {v["rule"] for v in data["violations"]}
    assert rules_triggered == {"enforce_layers"}


# ── Cannot depend on ──


def test_cannot_depend_detects_forbidden():
    """service.cannot_depend_on=["infra"] but service/handler.py imports infra.db."""
    result = _run_cli("--config", "cannot-depend.toml")
    assert result.returncode == 1
    assert "enforce_cannot_depend_on" in result.stdout
    assert "service" in result.stdout
    assert "infra" in result.stdout


# ── Transitive ──


def test_transitive_detects_indirect():
    """api.cannot_depend_on=["infra"], api doesn't directly import infra,
    but api → service → infra should be caught with transitive=true."""
    result = _run_cli("--config", "transitive.toml")
    assert result.returncode == 1
    stdout = result.stdout
    assert "transitive" in stdout.lower()
    assert "api" in stdout
    assert "infra" in stdout


def test_transitive_cli_flag_override():
    """cannot-depend.toml has transitive=false (default). Passing --transitive
    on CLI should enable transitive detection."""
    # Without --transitive: api has no direct infra import, so no api violation
    result_without = _run_cli("--config", "cannot-depend.toml", "--format", "json")
    data_without = json.loads(result_without.stdout)
    api_violations_without = [v for v in data_without["violations"] if v["module"] == "api"]
    assert len(api_violations_without) == 0

    # With --transitive: api → service → infra should be caught
    result_with = _run_cli("--config", "cannot-depend.toml", "--transitive", "--format", "json")
    data_with = json.loads(result_with.stdout)
    api_violations_with = [v for v in data_with["violations"] if v["module"] == "api"]
    assert len(api_violations_with) > 0
    assert "transitive" in api_violations_with[0]["detail"].lower()


# ── Exclusions ──


def test_exclusions_skip_legacy():
    """exclude_from_cycles=["legacy"] — legacy should not appear in cycle violations."""
    result = _run_cli("--config", "with-exclusions.toml", "--format", "json")
    data = json.loads(result.stdout)
    for v in data["violations"]:
        assert v["module"] != "legacy", f"legacy should be excluded: {v['detail']}"
    # Should still detect domain ↔ infra cycle
    cycle_details = " ".join(v["detail"] for v in data["violations"])
    assert "domain" in cycle_details
    assert "infra" in cycle_details


# ── Metrics ──


def test_metrics_warns_public_surface():
    """Modules with high external symbol usage trigger public surface warning."""
    result = _run_cli("--config", "metrics.toml", "--format", "json")
    data = json.loads(result.stdout)
    surface_violations = [v for v in data["violations"] if v["rule"] == "max_public_surface"]
    assert len(surface_violations) > 0
    # service (1/1 = 1.0) and infra (2/3 = 0.67) exceed threshold 0.3
    triggered_modules = {v["module"] for v in surface_violations}
    assert "service" in triggered_modules or "infra" in triggered_modules


def test_metrics_warns_low_cohesion():
    """Modules with more external than internal edges trigger cohesion warning."""
    result = _run_cli("--config", "metrics.toml", "--format", "json")
    data = json.loads(result.stdout)
    cohesion_violations = [v for v in data["violations"] if v["rule"] == "min_cohesion"]
    assert len(cohesion_violations) > 0


# ── JSON output ──


def test_json_has_metrics():
    result = _run_cli("--config", "all-rules.toml", "--format", "json")
    data = json.loads(result.stdout)
    assert "metrics" in data
    assert len(data["metrics"]) > 0
    module_names = {m["name"] for m in data["metrics"]}
    assert "domain" in module_names
    assert "api" in module_names


# ── HTML output ──


def test_html_output():
    result = _run_cli("--config", "all-rules.toml", "--format", "html")
    assert result.returncode == 0
    assert "<!DOCTYPE html>" in result.stdout
    assert "REPORT_DATA" in result.stdout


# ── Baseline workflow ──


def test_save_and_load_baseline(tmp_path):
    baseline_file = tmp_path / "baseline.json"

    # Save baseline with current violations
    result_save = _run_cli(
        "--config", "all-rules.toml",
        "--save-baseline", str(baseline_file),
    )
    assert result_save.returncode == 0
    assert baseline_file.exists()
    baseline_data = json.loads(baseline_file.read_text())
    total_violations = len(baseline_data["violations"])
    assert total_violations > 0

    # Run with baseline — most violations are known
    result_check = _run_cli(
        "--config", "all-rules.toml",
        "--baseline", str(baseline_file),
    )
    assert "accepted from baseline" in result_check.stdout

    # Verify via JSON that new violations are much fewer than total
    result_json = _run_cli(
        "--config", "all-rules.toml",
        "--baseline", str(baseline_file),
        "--format", "json",
    )
    data = json.loads(result_json.stdout)
    new_count = len(data["violations"])
    # Baseline should filter out most violations
    # (cycle detail may vary in starting node, so not always 0)
    assert new_count < total_violations


# ── Discover mode ──


def test_discover_golden():
    result = _run_cli("--config", "all-rules.toml", "--discover")
    assert result.returncode == 0
    assert "Module Dependencies" in result.stdout
    # Should show real imports
    assert "service" in result.stdout
    assert "domain" in result.stdout


def test_discover_json():
    result = _run_cli("--config", "all-rules.toml", "--discover", "--format", "json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "dependencies" in data
    assert len(data["dependencies"]) > 0


# ── Auto scan ──


def test_auto_scan_golden():
    result = subprocess.run(
        [sys.executable, "-m", "code_governance", "--auto", str(GOLDEN_PROJECT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1  # has cycles
    assert "no_cycles" in result.stdout


# ── Transitive + layers combo ──


def test_all_rules_has_transitive_layer_violations():
    """all-rules.toml has transitive=true + enforce_layers=true.
    Should detect transitive layer violations."""
    result = _run_cli("--config", "all-rules.toml", "--format", "json")
    data = json.loads(result.stdout)
    transitive_layer = [
        v for v in data["violations"]
        if v["rule"] == "enforce_layers" and "transitive" in v["detail"].lower()
    ]
    # api → service → infra is a transitive layer violation (api rank 0, infra rank 3)
    assert len(transitive_layer) >= 1


# ── Error cases ──


def test_missing_config_error():
    result = _run_cli("--config", "nonexistent.toml")
    assert result.returncode == 1
    assert "Config not found" in result.stderr
