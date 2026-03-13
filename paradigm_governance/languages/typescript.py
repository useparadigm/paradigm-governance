from __future__ import annotations

from ast_grep_py import SgNode

from paradigm_governance.schemas import ClassInfo, FileExtractionResult, ImportInfo


class TypeScriptPatterns:
    language = "typescript"
    extensions = (".ts", ".tsx", ".js", ".jsx")

    def extract(self, root: SgNode, file_path: str) -> FileExtractionResult:
        imports = self._extract_imports(root)
        classes = self._extract_classes(root)
        symbols = self._extract_symbols(root)
        return FileExtractionResult(
            file_path=file_path,
            imports=imports,
            classes=classes,
            symbols=symbols,
        )

    def _extract_imports(self, root: SgNode) -> list[ImportInfo]:
        results: list[ImportInfo] = []
        for node in root.find_all(kind="import_statement"):
            line = node.range().start.line + 1
            raw = node.text()
            source: str | None = None
            names: list[str] = []

            for child in node.children():
                if child.kind() == "string":
                    source = child.text().strip("'\"")
                elif child.kind() == "import_clause":
                    names = self._parse_import_clause(child)

            if source:
                if names:
                    for name in names:
                        results.append(ImportInfo(source_module=source, imported_name=name, line=line, raw_statement=raw))
                else:
                    results.append(ImportInfo(source_module=source, line=line, raw_statement=raw))
        return results

    def _parse_import_clause(self, clause: SgNode) -> list[str]:
        names: list[str] = []
        for child in clause.children():
            if child.kind() == "identifier":
                names.append(child.text())
            elif child.kind() == "named_imports":
                for spec in child.children():
                    if spec.kind() == "import_specifier":
                        name_node = spec.field("name")
                        if name_node:
                            names.append(name_node.text())
            elif child.kind() == "namespace_import":
                for sub in child.children():
                    if sub.kind() == "identifier":
                        names.append(sub.text())
        return names

    def _extract_classes(self, root: SgNode) -> list[ClassInfo]:
        results: list[ClassInfo] = []
        for node in root.find_all(kind="class_declaration"):
            name_node = node.field("name")
            if not name_node:
                continue
            name = name_node.text()
            bases: list[str] = []
            for heritage in node.find_all(kind="class_heritage"):
                for child in heritage.children():
                    if child.kind() == "extends_clause":
                        for sub in child.children():
                            if sub.kind() in ("type_identifier", "identifier", "member_expression"):
                                bases.append(sub.text())
                    elif child.kind() == "implements_clause":
                        for sub in child.children():
                            if sub.kind() in ("type_identifier", "identifier", "member_expression"):
                                bases.append(sub.text())
            results.append(ClassInfo(name=name, base_classes=bases))
        return results

    def _extract_symbols(self, root: SgNode) -> list[str]:
        symbols: list[str] = []
        for node in root.find_all(kind="class_declaration"):
            name = node.field("name")
            if name:
                symbols.append(name.text())
        for node in root.find_all(kind="function_declaration"):
            name = node.field("name")
            if name:
                symbols.append(name.text())
        for node in root.find_all(kind="variable_declarator"):
            name = node.field("name")
            value = node.field("value")
            if name and value and value.kind() == "arrow_function":
                symbols.append(name.text())
        return symbols
