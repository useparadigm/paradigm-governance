from __future__ import annotations

from ast_grep_py import SgNode

from paradigm_governance.schemas import ClassInfo, FileExtractionResult, ImportInfo


class CSharpPatterns:
    language = "csharp"
    extensions = (".cs",)

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
        for node in root.find_all(kind="using_directive"):
            line = node.range().start.line + 1
            raw = node.text()
            ns_parts: list[str] = []
            for child in node.children():
                if child.kind() in ("identifier", "qualified_name"):
                    ns_parts.append(child.text())
            if ns_parts:
                results.append(ImportInfo(source_module=ns_parts[0], line=line, raw_statement=raw))
        return results

    def _extract_classes(self, root: SgNode) -> list[ClassInfo]:
        results: list[ClassInfo] = []
        for node in root.find_all(kind="class_declaration"):
            name_node = node.field("name")
            if not name_node:
                continue
            name = name_node.text()
            bases: list[str] = []
            for base_list in node.find_all(kind="base_list"):
                for child in base_list.children():
                    if child.kind() in ("identifier", "qualified_name", "generic_name"):
                        bases.append(child.text())
            results.append(ClassInfo(name=name, base_classes=bases))
        return results

    def _extract_symbols(self, root: SgNode) -> list[str]:
        symbols: list[str] = []
        for node in root.find_all(kind="class_declaration"):
            name = node.field("name")
            if name:
                symbols.append(name.text())
        for node in root.find_all(kind="method_declaration"):
            name = node.field("name")
            if name:
                symbols.append(name.text())
        for node in root.find_all(kind="interface_declaration"):
            name = node.field("name")
            if name:
                symbols.append(name.text())
        return symbols
