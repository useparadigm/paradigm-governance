from __future__ import annotations

from pathlib import Path

import pytest

from code_governance.languages.typescript import TypeScriptPatterns
from code_governance.schemas import GovernanceConfig, Language, ModuleConfig


def _make_patterns(tmp_path: Path, tsconfig_body: str | None = None) -> TypeScriptPatterns:
    if tsconfig_body is not None:
        (tmp_path / "tsconfig.json").write_text(tsconfig_body)
    cfg = GovernanceConfig(
        root=".",
        language=Language.TYPESCRIPT,
        modules=[
            ModuleConfig(name="api", path="src/api/"),
            ModuleConfig(name="core", path="src/core/"),
            ModuleConfig(name="db", path="src/db/"),
        ],
    )
    p = TypeScriptPatterns()
    p.initialize(tmp_path, cfg)
    return p


def _importable_map() -> dict[str, str]:
    return {
        "src/core/models": "core",
        "src/core/index": "core",
        "src/db/repository": "db",
        "src/db/index": "db",
        "src/api/routes": "api",
    }


def test_resolve_relative_sibling(tmp_path):
    p = _make_patterns(tmp_path)
    cfg = GovernanceConfig(language=Language.TYPESCRIPT)
    assert p.resolve_import("./models", "src/core/service.ts", cfg, _importable_map(), {}) == "core"


def test_resolve_relative_parent(tmp_path):
    p = _make_patterns(tmp_path)
    cfg = GovernanceConfig(language=Language.TYPESCRIPT)
    assert p.resolve_import("../db/repository", "src/core/service.ts", cfg, _importable_map(), {}) == "db"


def test_resolve_relative_to_index(tmp_path):
    p = _make_patterns(tmp_path)
    cfg = GovernanceConfig(language=Language.TYPESCRIPT)
    # Import './db' from a file in src/; should find src/db/index
    assert p.resolve_import("../db", "src/api/routes.ts", cfg, _importable_map(), {}) == "db"


def test_alias_wildcard(tmp_path):
    p = _make_patterns(
        tmp_path,
        '{"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["src/*"]}}}',
    )
    cfg = GovernanceConfig(language=Language.TYPESCRIPT)
    assert p.resolve_import("@/core/models", "src/api/routes.ts", cfg, _importable_map(), {}) == "core"


def test_bare_specifier_returns_none(tmp_path):
    p = _make_patterns(tmp_path)
    cfg = GovernanceConfig(language=Language.TYPESCRIPT)
    assert p.resolve_import("lodash", "src/api/routes.ts", cfg, _importable_map(), {}) is None
    assert p.resolve_import("@scope/pkg", "src/api/routes.ts", cfg, _importable_map(), {}) is None


def test_missing_file_returns_none(tmp_path):
    p = _make_patterns(tmp_path)
    cfg = GovernanceConfig(language=Language.TYPESCRIPT)
    assert p.resolve_import("./ghost", "src/core/service.ts", cfg, _importable_map(), {}) is None


def test_file_to_importable_strips_all_ts_js_extensions(tmp_path):
    p = _make_patterns(tmp_path)
    assert p.file_to_importable("src/a/b.ts") == "src/a/b"
    assert p.file_to_importable("src/a/b.tsx") == "src/a/b"
    assert p.file_to_importable("src/a/b.js") == "src/a/b"
    assert p.file_to_importable("src/a/b.jsx") == "src/a/b"
    assert p.file_to_importable("src/a/b.py") is None
