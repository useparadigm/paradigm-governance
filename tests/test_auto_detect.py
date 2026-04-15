from __future__ import annotations

from code_governance.engine import detect_language
from code_governance.schemas import Language


def test_python_dominant(tmp_path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.py").write_text("")
    (tmp_path / "c.ts").write_text("")
    assert detect_language(tmp_path) == Language.PYTHON


def test_typescript_dominant(tmp_path):
    (tmp_path / "a.ts").write_text("")
    (tmp_path / "b.tsx").write_text("")
    (tmp_path / "c.py").write_text("")
    assert detect_language(tmp_path) == Language.TYPESCRIPT


def test_empty_defaults_to_python(tmp_path):
    assert detect_language(tmp_path) == Language.PYTHON


def test_skips_node_modules(tmp_path):
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "index.ts").write_text("")
    (nm / "a.ts").write_text("")
    (nm / "b.ts").write_text("")
    (tmp_path / "main.py").write_text("")
    assert detect_language(tmp_path) == Language.PYTHON
