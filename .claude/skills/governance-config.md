# Skill: Generate governance.toml configuration

Use this skill when asked to set up governance rules for a Python project, create a governance.toml, or brainstorm module boundaries and architecture layers.

## Step 1: Generate ground-truth config

Start by generating a config from the actual codebase:

```bash
governance-ast --generate --source-root <path-to-source> --config governance.toml
```

This creates a `governance.toml` with:
- All top-level directories as modules
- Real `depends_on` populated from actual imports
- No enforcement rules (ground truth only)

## Step 2: Read and analyze the generated config

Read the generated `governance.toml` and also run discovery to understand the dependency structure:

```bash
governance-ast --discover --format json
```

## Step 3: Brainstorm architecture decisions

Now enrich the config by reasoning about the codebase:

### Assign layers
Categorize each module into an architectural layer. Common patterns:

**Web app layers** (top to bottom):
- `presentation` — routes, views, templates, CLI
- `application` — use cases, services, orchestration
- `domain` — business logic, models, rules
- `infrastructure` — database, external APIs, file I/O
- `shared` — utilities, constants, types used everywhere

**Data pipeline layers**:
- `ingestion` — data sources, readers
- `processing` — transforms, validation
- `storage` — writers, exporters
- `orchestration` — scheduling, coordination

Set `layers.order` from highest to lowest. Higher layers may import from lower layers, not vice versa.

### Prune depends_on
The auto-generated `depends_on` reflects reality. Now decide what SHOULD be allowed:
- Remove dependencies that represent architecture violations
- Keep dependencies that are intentional

### Enable rules
```toml
[rules]
no_cycles = true              # Almost always enable
enforce_depends_on = true      # Enable once depends_on is curated
enforce_layers = true          # Enable once layers are assigned
exclude_test_files = true      # Usually true
# max_public_surface = 0.5     # Optional: warn on leaky modules
# min_cohesion = 0.3           # Optional: warn on fragmented modules
```

### Consider cycle exclusions
Some modules (like `shared` or `utils`) may legitimately participate in cycles. Exclude them:
```toml
exclude_from_cycles = ["shared", "utils"]
```

## Step 4: Validate

Run the checks and see what violations appear:

```bash
governance-ast
```

If there are too many violations to fix immediately, create a baseline:

```bash
governance-ast --save-baseline .governance-baseline.json
```

## Step 5: Iterate

The config is a living document. As the codebase evolves:
- Add new modules when new directories appear
- Update `depends_on` when architecture changes
- Tighten rules gradually (enable layers, lower thresholds)

## Example enriched config

```toml
[governance]
root = "src"
language = "python"

[[modules]]
name = "api"
path = "api/"
depends_on = ["services", "models"]
layer = "presentation"

[[modules]]
name = "services"
path = "services/"
depends_on = ["models", "repositories"]
layer = "application"

[[modules]]
name = "models"
path = "models/"
depends_on = []
layer = "domain"

[[modules]]
name = "repositories"
path = "repositories/"
depends_on = ["models"]
layer = "infrastructure"

[[modules]]
name = "utils"
path = "utils/"
depends_on = []
layer = "shared"

[layers]
order = ["presentation", "application", "domain", "infrastructure", "shared"]

[rules]
no_cycles = true
enforce_layers = true
enforce_depends_on = true
exclude_test_files = true
exclude_from_cycles = ["utils"]
```
