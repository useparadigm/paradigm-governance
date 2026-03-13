from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from paradigm_governance.schemas import (
    EdgeDetail,
    FileExtractionResult,
    GovernanceConfig,
    ModuleConfig,
)


@dataclass
class DepEdge:
    source: str
    target: str
    count: int = 1


@dataclass
class DependencyGraph:
    module_edges: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    file_edges: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    module_internal_edges: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    module_external_edges: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    symbols_per_module: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    externally_used_symbols: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    edge_details: list[EdgeDetail] = field(default_factory=list)

    def get_module_dependencies(self, module_name: str) -> set[str]:
        return set(self.module_edges.get(module_name, {}).keys())


def build_dependency_graph(
    extractions: list[FileExtractionResult],
    config: GovernanceConfig,
) -> DependencyGraph:
    graph = DependencyGraph()
    file_to_module = _build_file_to_module_map(extractions, config)
    module_files = _build_module_files_map(config)
    importable_map = _build_importable_map(extractions, config)

    for ext in extractions:
        src_module = file_to_module.get(ext.file_path)
        if not src_module:
            continue

        for sym in ext.symbols:
            graph.symbols_per_module[src_module].add(sym)

        for imp in ext.imports:
            target_module = _resolve_import_to_module(
                imp.source_module, ext.file_path, config, importable_map, module_files
            )
            if not target_module:
                continue

            graph.file_edges[ext.file_path][imp.source_module] += 1

            if target_module == src_module:
                graph.module_internal_edges[src_module] += 1
            else:
                graph.module_edges[src_module][target_module] += 1
                graph.module_external_edges[src_module] += 1
                if imp.imported_name:
                    graph.externally_used_symbols[target_module].add(imp.imported_name)
                graph.edge_details.append(EdgeDetail(
                    source_file=ext.file_path,
                    source_module=src_module,
                    target_module=target_module,
                    imported_name=imp.imported_name,
                    line=imp.line,
                    raw_statement=imp.raw_statement,
                ))

    return graph


def _build_file_to_module_map(
    extractions: list[FileExtractionResult],
    config: GovernanceConfig,
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for ext in extractions:
        for mod in config.modules:
            mod_path = mod.path.rstrip("/")
            if ext.file_path == mod_path or ext.file_path.startswith(mod_path + "/"):
                mapping[ext.file_path] = mod.name
                break
    return mapping


def _build_module_files_map(config: GovernanceConfig) -> dict[str, str]:
    return {mod.name: mod.path.rstrip("/") for mod in config.modules}


def _build_importable_map(
    extractions: list[FileExtractionResult],
    config: GovernanceConfig,
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for ext in extractions:
        for mod in config.modules:
            mod_path = mod.path.rstrip("/")
            if ext.file_path.startswith(mod_path + "/") or ext.file_path == mod_path:
                dotted = _file_to_dotted(ext.file_path, config)
                if dotted:
                    mapping[dotted] = mod.name
                break
    return mapping


def _file_to_dotted(file_path: str, config: GovernanceConfig) -> str | None:
    p = PurePosixPath(file_path)
    if p.suffix in (".py",):
        stem = str(p.with_suffix("")).replace("/", ".")
        return stem
    elif p.suffix in (".ts", ".tsx", ".js", ".jsx"):
        stem = str(p.with_suffix("")).replace("/", ".")
        return stem
    elif p.suffix in (".cs",):
        return None
    return None


def _resolve_import_to_module(
    import_source: str,
    importing_file: str,
    config: GovernanceConfig,
    importable_map: dict[str, str],
    module_files: dict[str, str],
) -> str | None:
    if config.language.value == "python":
        return _resolve_python_import(import_source, importing_file, config, importable_map, module_files)
    elif config.language.value == "typescript":
        return _resolve_ts_import(import_source, importing_file, config, module_files)
    elif config.language.value == "csharp":
        return _resolve_csharp_import(import_source, config)
    return None


def _resolve_python_import(
    import_source: str,
    importing_file: str,
    config: GovernanceConfig,
    importable_map: dict[str, str],
    module_files: dict[str, str],
) -> str | None:
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

    for candidate in candidates:
        if candidate in importable_map:
            return importable_map[candidate]

        for dotted, mod_name in importable_map.items():
            if dotted.startswith(candidate + ".") or candidate.startswith(dotted + "."):
                return mod_name

        for mod in config.modules:
            mod_prefix = mod.path.rstrip("/").replace("/", ".")
            if candidate == mod_prefix or candidate.startswith(mod_prefix + "."):
                return mod.name

    return None


def _resolve_relative_import(import_source: str, importing_file: str) -> str | None:
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


def _resolve_ts_import(
    import_source: str,
    importing_file: str,
    config: GovernanceConfig,
    module_files: dict[str, str],
) -> str | None:
    if not import_source.startswith("."):
        return None

    importing_dir = str(PurePosixPath(importing_file).parent)
    resolved = str(PurePosixPath(importing_dir) / import_source)
    resolved = _normalize_path(resolved)

    for mod_name, mod_path in module_files.items():
        mod_path_clean = mod_path.rstrip("/")
        if resolved.startswith(mod_path_clean + "/") or resolved == mod_path_clean:
            return mod_name

    return None


def _resolve_csharp_import(
    import_source: str,
    config: GovernanceConfig,
) -> str | None:
    for mod in config.modules:
        if (
            import_source == mod.name
            or import_source.startswith(mod.name + ".")
        ):
            return mod.name
    return None


def _normalize_path(path: str) -> str:
    parts: list[str] = []
    for part in path.split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)
