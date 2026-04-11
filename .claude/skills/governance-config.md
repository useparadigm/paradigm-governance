# Skill: Generate governance.toml configuration

Use this skill when asked to set up governance rules for a Python project, create a governance.toml, or brainstorm module boundaries and architecture layers.

## Step 1: Generate ground-truth config

Start by generating a config from the actual codebase:

```bash
governance-ast --generate --source-root <path-to-source> --config governance.toml
```

This creates a `governance.toml` with:
- All top-level directories as modules
- Empty `cannot_depend_on` (no restrictions by default)
- Default enforcement rules

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

### Add forbidden dependencies
By default, all imports are allowed. Add modules to `cannot_depend_on` to block unwanted dependencies:
- Identify cross-module imports that violate your architecture
- Add forbidden targets to `cannot_depend_on`

### Enable rules
```toml
[rules]
no_cycles = true              # Almost always enable
enforce_cannot_depend_on = true # Enable to enforce forbidden imports
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
- Update `cannot_depend_on` when architecture changes
- Tighten rules gradually (enable layers, lower thresholds)

## Example enriched config

```toml
[governance]
root = "src"
language = "python"

[[modules]]
name = "api"
path = "api/"
cannot_depend_on = ["repositories"]
layer = "presentation"

[[modules]]
name = "services"
path = "services/"
cannot_depend_on = []
layer = "application"

[[modules]]
name = "models"
path = "models/"
cannot_depend_on = ["api", "services", "repositories"]
layer = "domain"

[[modules]]
name = "repositories"
path = "repositories/"
cannot_depend_on = ["api", "services"]
layer = "infrastructure"

[[modules]]
name = "utils"
path = "utils/"
cannot_depend_on = ["api", "services", "repositories"]
layer = "shared"

[layers]
order = ["presentation", "application", "domain", "infrastructure", "shared"]

[rules]
no_cycles = true
enforce_layers = true
enforce_cannot_depend_on = true
exclude_test_files = true
exclude_from_cycles = ["utils"]
```
