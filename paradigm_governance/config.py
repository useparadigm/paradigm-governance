from __future__ import annotations

import tomllib
from pathlib import Path

from paradigm_governance.schemas import (
    GovernanceConfig,
    LayersConfig,
    ModuleConfig,
    RulesConfig,
)


def load_config(config_path: str | Path) -> GovernanceConfig:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "rb") as f:
        raw = tomllib.load(f)

    gov = raw.get("governance", {})
    modules_raw = raw.get("modules", [])
    layers_raw = raw.get("layers", {})
    rules_raw = raw.get("rules", {})

    modules = [ModuleConfig(**m) for m in modules_raw]
    layers = LayersConfig(**layers_raw) if layers_raw else LayersConfig()
    rules = RulesConfig(**rules_raw) if rules_raw else RulesConfig()

    return GovernanceConfig(
        root=gov.get("root", "."),
        language=gov.get("language", "python"),
        package_prefix=gov.get("package_prefix"),
        modules=modules,
        layers=layers,
        rules=rules,
    )
