from __future__ import annotations

from ast_grep_py import SgNode

from paradigm_governance.schemas import ClassInfo, FileExtractionResult, ImportInfo


class PythonPatterns:
    language = "python"
    extensions = (".py",)

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
            for child in node.children():
                if child.kind() in ("dotted_name", "aliased_import"):
                    mod = child.text().split(" as ")[0]
                    results.append(ImportInfo(source_module=mod, line=line, raw_statement=raw))

        for node in root.find_all(kind="import_from_statement"):
            line = node.range().start.line + 1
            raw = node.text()
            mod_node = None
            names: list[str] = []
            for child in node.children():
                if child.kind() in ("dotted_name", "relative_import"):
                    if mod_node is None:
                        mod_node = child
                    else:
                        names.append(child.text())
                elif child.kind() == "wildcard_import":
                    names.append("*")

            mod = mod_node.text() if mod_node else ""
            if names:
                for name in names:
                    results.append(ImportInfo(source_module=mod, imported_name=name, line=line, raw_statement=raw))
            else:
                results.append(ImportInfo(source_module=mod, line=line, raw_statement=raw))

        return results

    def _extract_classes(self, root: SgNode) -> list[ClassInfo]:
        results: list[ClassInfo] = []
        for node in root.find_all(kind="class_definition"):
            name_node = node.field("name")
            if not name_node:
                continue
            name = name_node.text()
            bases: list[str] = []
            superclasses = node.field("superclasses")
            if superclasses:
                for child in superclasses.children():
                    if child.kind() not in ("(", ")", ","):
                        bases.append(child.text())
            results.append(ClassInfo(name=name, base_classes=bases))
        return results

    def _extract_symbols(self, root: SgNode) -> list[str]:
        symbols: list[str] = []
        for node in root.find_all(kind="class_definition"):
            name = node.field("name")
            if name:
                symbols.append(name.text())
        for node in root.find_all(kind="function_definition"):
            name = node.field("name")
            if name:
                symbols.append(name.text())
        return symbols
