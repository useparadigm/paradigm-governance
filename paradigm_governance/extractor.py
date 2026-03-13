from __future__ import annotations

from pathlib import Path

from ast_grep_py import SgRoot

from paradigm_governance.languages import get_patterns
from paradigm_governance.schemas import FileExtractionResult, Language


def extract_file(file_path: str, source: str, language: Language) -> FileExtractionResult:
    patterns = get_patterns(language)
    root = SgRoot(source, patterns.language)
    return patterns.extract(root.root(), file_path)


def extract_directory(
    root_dir: str | Path,
    language: Language,
    exclude_test_files: bool = True,
) -> list[FileExtractionResult]:
    patterns = get_patterns(language)
    root_path = Path(root_dir)
    results: list[FileExtractionResult] = []

    for ext in patterns.extensions:
        for file_path in root_path.rglob(f"*{ext}"):
            if _should_skip(file_path):
                continue
            rel_path = str(file_path.relative_to(root_path))
            if exclude_test_files and _is_test_file(rel_path, language):
                continue
            try:
                source = file_path.read_text(encoding="utf-8", errors="replace")
                result = extract_file(rel_path, source, language)
                results.append(result)
            except Exception:
                continue

    return results


_TEST_DIR_SEGMENTS = {"tests", "test", "__tests__"}

_TEST_FILE_PATTERNS: dict[Language, list[tuple[str, str]]] = {
    Language.PYTHON: [("test_", ""), ("", "_test.py"), ("conftest.py", "")],
    Language.TYPESCRIPT: [
        ("", ".test.ts"), ("", ".test.tsx"),
        ("", ".spec.ts"), ("", ".spec.tsx"),
    ],
    Language.CSHARP: [("", "Tests.cs"), ("", "Test.cs")],
}


def _is_test_file(rel_path: str, language: Language) -> bool:
    parts = rel_path.replace("\\", "/").split("/")
    if any(p in _TEST_DIR_SEGMENTS for p in parts[:-1]):
        return True
    filename = parts[-1]
    for prefix, suffix in _TEST_FILE_PATTERNS.get(language, []):
        if prefix and filename.startswith(prefix):
            return True
        if suffix and filename.endswith(suffix):
            return True
    return False


def _should_skip(path: Path) -> bool:
    skip_dirs = {
        "__pycache__", ".git", "node_modules", ".venv", "venv",
        ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
        ".eggs", "bin", "obj",
    }
    return any(part in skip_dirs for part in path.parts)
