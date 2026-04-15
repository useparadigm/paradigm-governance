import json
import subprocess
import sys
from pathlib import Path

SAMPLE_TS_PROJECT = Path(__file__).parent / "fixtures" / "sample_ts_project"


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "code_governance", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


def test_check_text_on_ts_fixture():
    result = _run("--config", "governance.toml", cwd=SAMPLE_TS_PROJECT)
    assert result.returncode == 1
    assert "Governance Report (typescript)" in result.stdout
    assert "Violations" in result.stdout
    assert "no_cycles" in result.stdout
    assert "enforce_cannot_depend_on" in result.stdout


def test_check_json_on_ts_fixture():
    result = _run("--config", "governance.toml", "--format", "json", cwd=SAMPLE_TS_PROJECT)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["language"] == "typescript"
    assert len(data["violations"]) > 0


def test_discover_on_ts_fixture():
    result = _run("--config", "governance.toml", "--discover", "--format", "json", cwd=SAMPLE_TS_PROJECT)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["language"] == "typescript"
    # alias-resolved edge must be present
    db_deps = {t["target"] for t in data["dependencies"].get("db", [])}
    assert "core" in db_deps


def test_auto_on_ts_fixture_detects_language():
    result = _run("--auto", str(SAMPLE_TS_PROJECT))
    assert "Governance Report (typescript)" in result.stdout


def test_auto_on_ts_with_explicit_language_flag(tmp_path):
    (tmp_path / "a.ts").write_text("import { x } from './b';")
    (tmp_path / "b.ts").write_text("export const x = 1;")
    result = _run(
        "--generate",
        "--source-root", str(tmp_path),
        "--language", "typescript",
        "--config", str(tmp_path / "governance.toml"),
    )
    assert result.returncode == 0, result.stderr
    content = (tmp_path / "governance.toml").read_text()
    assert 'language = "typescript"' in content


def test_generate_auto_picks_typescript(tmp_path):
    for name in ("one.ts", "two.ts", "three.tsx"):
        (tmp_path / name).write_text("export const x = 1;")
    (tmp_path / "scratch.py").write_text("")
    result = _run(
        "--generate",
        "--source-root", str(tmp_path),
        "--config", str(tmp_path / "governance.toml"),
    )
    assert result.returncode == 0, result.stderr
    content = (tmp_path / "governance.toml").read_text()
    assert 'language = "typescript"' in content


def test_ci_report_on_ts_fixture():
    result = subprocess.run(
        [sys.executable, "-m", "code_governance.ci_report", "--config", "governance.toml", "--json"],
        capture_output=True, text=True, cwd=str(SAMPLE_TS_PROJECT),
    )
    # Exit 1 is expected when violations exist — same contract as --format json
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["passed"] is False
    assert len(data["violations"]) > 0
    assert "markdown" in data
    assert "src/core/service.ts" in data["markdown"]


def test_html_on_ts_fixture():
    result = _run("--config", "governance.toml", "--format", "html", cwd=SAMPLE_TS_PROJECT)
    assert result.returncode == 0
    assert "<!DOCTYPE html>" in result.stdout
    assert "typescript" in result.stdout.lower()
