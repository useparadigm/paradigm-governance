from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Optional

from ast_grep_py import SgNode

from code_governance.schemas import ClassInfo, FileExtractionResult, ImportInfo

if TYPE_CHECKING:
    from code_governance.schemas import GovernanceConfig


class PythonPatterns:
    language = "python"
    extensions = (".py",)
    test_file_patterns: list[tuple[str, str]] = [
        ("test_", ""),
        ("", "_test.py"),
        ("conftest.py", ""),
    ]

    def initialize(self, repo_root: Path, config: "GovernanceConfig") -> None:
        pass

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

    def file_to_importable(self, file_path: str) -> Optional[str]:
        p = PurePosixPath(file_path)
        if p.suffix == ".py":
            return str(p.with_suffix("")).replace("/", ".")
        return None

    def resolve_import(
        self,
        import_source: str,
        importing_file: str,
        config: "GovernanceConfig",
        importable_map: dict[str, str],
        module_files: dict[str, str],
    ) -> Optional[str]:
        if import_source.startswith("."):
            resolved = _resolve_relative_import(import_source, importing_file)
            if resolved:
                import_source = resolved

        candidates = [import_source]
        root_pkg = config.root.rstrip("/").replace("/", ".")
        if import_source.startswith(root_pkg + "."):
            candidates.append(import_source[len(root_pkg) + 1:])
        if config.package_prefix and import_source.startswith(config.package_prefix + "."):
            candidates.append(import_source[len(config.package_prefix) + 1:])

        sorted_mods = sorted(
            config.modules,
            key=lambda m: len(m.path.rstrip("/").split("/")) if m.path not in (".", "./") else 0,
            reverse=True,
        )

        for candidate in candidates:
            if candidate in importable_map:
                return importable_map[candidate]

            best_match: Optional[str] = None
            best_len = -1
            for dotted, mod_name in importable_map.items():
                if dotted.startswith(candidate + ".") or candidate.startswith(dotted + "."):
                    if len(dotted) > best_len:
                        best_len = len(dotted)
                        best_match = mod_name
            if best_match:
                return best_match

            for mod in sorted_mods:
                mod_prefix = mod.path.rstrip("/").replace("/", ".")
                if candidate == mod_prefix or candidate.startswith(mod_prefix + "."):
                    return mod.name

        return None

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


def _resolve_relative_import(import_source: str, importing_file: str) -> Optional[str]:
    dots = 0
    for ch in import_source:
        if ch == ".":
            dots += 1
        else:
            break

    remainder = import_source[dots:]
    parts = PurePosixPath(importing_file).parts[:-1]

    if dots > len(parts):
        return None

    base_parts = parts[: len(parts) - (dots - 1)]
    if remainder:
        return ".".join(base_parts) + "." + remainder
    return ".".join(base_parts)
