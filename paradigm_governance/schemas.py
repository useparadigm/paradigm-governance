from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Language(str, Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    CSHARP = "csharp"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RuleKind(str, Enum):
    NO_CYCLES = "no_cycles"
    ENFORCE_LAYERS = "enforce_layers"
    ENFORCE_DEPENDS_ON = "enforce_depends_on"
    MAX_PUBLIC_SURFACE = "max_public_surface"
    MIN_COHESION = "min_cohesion"


class ModuleConfig(BaseModel):
    name: str
    path: str
    depends_on: list[str] = []
    layer: Optional[str] = None


class LayersConfig(BaseModel):
    order: list[str] = []


class RulesConfig(BaseModel):
    no_cycles: bool = True
    enforce_layers: bool = False
    enforce_depends_on: bool = True
    max_public_surface: Optional[float] = None
    min_cohesion: Optional[float] = None
    exclude_from_cycles: list[str] = []
    exclude_test_files: bool = True


class GovernanceConfig(BaseModel):
    root: str = "."
    language: Language = Language.PYTHON
    package_prefix: Optional[str] = None
    modules: list[ModuleConfig] = []
    layers: LayersConfig = LayersConfig()
    rules: RulesConfig = RulesConfig()


@dataclass
class ImportInfo:
    source_module: str
    imported_name: Optional[str] = None
    line: int = 0
    raw_statement: str = ""


@dataclass
class EdgeDetail:
    source_file: str
    source_module: str
    target_module: str
    imported_name: Optional[str]
    line: int
    raw_statement: str


@dataclass
class ClassInfo:
    name: str
    base_classes: list[str] = field(default_factory=list)


@dataclass
class FileExtractionResult:
    file_path: str
    imports: list[ImportInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)


class Violation(BaseModel):
    rule: RuleKind
    module: str
    detail: str
    severity: Severity = Severity.ERROR
    evidence: list[dict] = []


class ModuleMetrics(BaseModel):
    name: str
    total_symbols: int = 0
    externally_used_symbols: int = 0
    internal_edges: int = 0
    external_edges: int = 0
    public_surface_ratio: Optional[float] = None
    cohesion_ratio: Optional[float] = None


class DependencyTarget(BaseModel):
    target: str
    count: int
    files: list[dict] = []


class DiscoverReport(BaseModel):
    config_path: str
    language: Language
    module_count: int
    total_files_scanned: int
    dependencies: dict[str, list[DependencyTarget]] = {}
    metrics: list["ModuleMetrics"] = []


class GovernanceReport(BaseModel):
    config_path: str
    language: Language
    module_count: int
    total_files_scanned: int
    violations: list[Violation] = []
    metrics: list[ModuleMetrics] = []

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0
