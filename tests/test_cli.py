import subprocess
import sys
from pathlib import Path

SAMPLE_PROJECT = Path(__file__).parent / "fixtures" / "sample_project"


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "paradigm_governance", *args],
        capture_output=True,
        text=True,
        cwd=str(SAMPLE_PROJECT),
    )


def test_cli_check_text():
    result = _run_cli("--config", "governance.toml")
    assert result.returncode == 1  # has violations
    assert "Governance Report" in result.stdout
    assert "Violations" in result.stdout


def test_cli_check_json():
    result = _run_cli("--config", "governance.toml", "--format", "json")
    assert result.returncode == 1
    import json
    data = json.loads(result.stdout)
    assert "violations" in data
    assert len(data["violations"]) > 0


def test_cli_discover():
    result = _run_cli("--config", "governance.toml", "--discover")
    assert result.returncode == 0
    assert "Module Dependencies" in result.stdout


def test_cli_discover_json():
    result = _run_cli("--config", "governance.toml", "--discover", "--format", "json")
    assert result.returncode == 0
    import json
    data = json.loads(result.stdout)
    assert "dependencies" in data


def test_cli_fix_config(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "paradigm_governance",
         "--fix-config", "--source-root", str(SAMPLE_PROJECT),
         "--config", str(tmp_path / "governance.toml")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "governance.toml").exists()
    content = (tmp_path / "governance.toml").read_text()
    assert "core" in content


def test_cli_generate(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "paradigm_governance",
         "--generate", "--source-root", str(SAMPLE_PROJECT),
         "--config", str(tmp_path / "governance.toml")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "governance.toml").exists()


def test_cli_html():
    result = _run_cli("--config", "governance.toml", "--format", "html")
    assert result.returncode == 0
    assert "<!DOCTYPE html>" in result.stdout
    assert "REPORT_DATA" in result.stdout


def test_cli_missing_config():
    result = _run_cli("--config", "nonexistent.toml")
    assert result.returncode == 1
    assert "Config not found" in result.stderr


def test_cli_auto():
    result = subprocess.run(
        [sys.executable, "-m", "paradigm_governance", "--auto", str(SAMPLE_PROJECT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1  # has cycle: core <-> db
    assert "Governance Report" in result.stdout
    assert "no_cycles" in result.stdout
    assert "auto-scan" in result.stdout


def test_cli_auto_json():
    result = subprocess.run(
        [sys.executable, "-m", "paradigm_governance", "--auto", str(SAMPLE_PROJECT), "--format", "json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    import json
    data = json.loads(result.stdout)
    assert data["config_path"] == "(auto-scan)"
    assert len(data["violations"]) > 0
