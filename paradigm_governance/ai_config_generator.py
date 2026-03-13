from __future__ import annotations

import os
import time
from pathlib import Path

from openai import OpenAI, RateLimitError

from paradigm_governance.schemas import GovernanceConfig

MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0

SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", "venv", ".venv",
    "dist", "build", ".tox", ".egg-info", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "bin", "obj",
}

LANGUAGE_EXTENSIONS: dict[str, set[str]] = {
    "python": {".py"},
    "typescript": {".ts", ".tsx", ".js", ".jsx"},
    "csharp": {".cs"},
}

MAX_DEPTH = 4

SYSTEM_PROMPT = """\
You are a software architect. You are given a governance.toml config file and a directory tree for a codebase.

governance.toml defines module boundaries and architecture rules:
- **modules**: each has a `name`, `path` (relative dir), `depends_on` (list of module names it may import from), and optional `layer`.
- **layers.order**: ordered list of layer names from highest to lowest. Higher layers may depend on lower, not vice versa.
- **rules**: boolean flags — `no_cycles`, `enforce_layers`, `enforce_depends_on`, `exclude_test_files`.

Your job: enrich the pre-filled config with sensible architecture decisions.
1. Assign a `layer` to each module (e.g. "api", "domain", "infrastructure", "shared").
2. Define `layers.order` from highest to lowest.
3. Toggle rules: enable `enforce_layers` if you assigned layers, keep `no_cycles` and `enforce_depends_on` true.
4. You may rename modules if the folder name is unclear, or merge tiny related modules.
5. Leave `depends_on` as empty lists — dependencies will be auto-populated from actual imports later.
6. Keep `exclude_test_files = true`.
"""


def collect_repo_tree(source_root: Path, language: str) -> str:
    extensions = LANGUAGE_EXTENSIONS.get(language, set())
    lines: list[str] = []

    def _walk(directory: Path, prefix: str, depth: int):
        if depth > MAX_DEPTH:
            return
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        except PermissionError:
            return

        dirs = [e for e in entries if e.is_dir() and e.name not in SKIP_DIRS and not e.name.startswith(".")]
        files = [e for e in entries if e.is_file() and e.suffix in extensions]

        items = dirs + files
        for i, entry in enumerate(items):
            connector = "└── " if i == len(items) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                extension = "    " if i == len(items) - 1 else "│   "
                _walk(entry, prefix + extension, depth + 1)

    lines.append(f"{source_root.name}/")
    _walk(source_root, "", 1)
    return "\n".join(lines)


def enrich_config_via_ai(base_config_toml: str, tree: str) -> GovernanceConfig:
    client = OpenAI()

    user_prompt = f"""\
Here is the pre-filled governance.toml:

```toml
{base_config_toml}
```

Here is the directory tree:

```
{tree}
```

Enrich this config: assign layers, define layer order, toggle rules, and optionally rename or merge modules. Return the full GovernanceConfig."""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.responses.parse(
                model=os.environ.get("GOVERNANCE_AI_MODEL", "gpt-5-nano"),
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                text_format=GovernanceConfig,
            )
            return response.output_parsed
        except RateLimitError:
            if attempt < MAX_RETRIES - 1:
                wait = INITIAL_BACKOFF * (2 ** attempt)
                time.sleep(wait)
            else:
                raise
