from __future__ import annotations

import pytest

from code_governance.extractor import extract_file
from code_governance.schemas import Language


def _imports(source: str) -> list[tuple[str, str | None]]:
    result = extract_file("src/file.ts", source, Language.TYPESCRIPT)
    return [(i.source_module, i.imported_name) for i in result.imports]


def test_default_import():
    assert _imports("import Foo from './foo';") == [("./foo", "Foo")]


def test_named_imports_produce_multiple_rows():
    assert _imports("import { A, B } from './foo';") == [("./foo", "A"), ("./foo", "B")]


def test_namespace_import():
    assert _imports("import * as utils from './utils';") == [("./utils", "utils")]


def test_side_effect_import():
    assert _imports("import './style.css';") == [("./style.css", None)]


def test_type_only_import_is_counted():
    assert _imports("import type { T } from './types';") == [("./types", "T")]


def test_mixed_default_and_named():
    rows = _imports("import React, { useState } from 'react';")
    assert ("react", "React") in rows
    assert ("react", "useState") in rows


def test_re_export_named():
    assert _imports("export { X } from './x';") == [("./x", "X")]


def test_re_export_star():
    rows = _imports("export * from './y';")
    assert rows == [("./y", None)]


def test_require_literal():
    rows = _imports("const lib = require('./lib');")
    assert rows == [("./lib", None)]


def test_ignores_require_with_variable():
    rows = _imports("const lib = require(pkg);")
    assert rows == []


def test_classes_and_bases():
    src = "export class Service extends Base implements IX { m() {} }"
    result = extract_file("src/file.ts", src, Language.TYPESCRIPT)
    assert result.classes[0].name == "Service"
    assert "Base" in result.classes[0].base_classes
    assert "IX" in result.classes[0].base_classes


def test_symbols_collect_top_level_declarations():
    src = """
    export class C {}
    function f() {}
    const X = 1;
    interface I {}
    type T = string;
    """
    result = extract_file("src/file.ts", src, Language.TYPESCRIPT)
    assert set(result.symbols) >= {"C", "f", "X", "I", "T"}


@pytest.mark.parametrize("ext", [".ts", ".tsx", ".js", ".jsx"])
def test_handles_all_extensions(ext):
    result = extract_file(f"src/file{ext}", "import X from './y';", Language.TYPESCRIPT)
    assert result.imports == [("./y", "X")] or [(i.source_module, i.imported_name) for i in result.imports] == [("./y", "X")]
