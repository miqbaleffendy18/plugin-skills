# Why a Custom Plugin Instead of a Marketplace Skill

## The short answer

Public marketplace skills are general-purpose. They cannot know your internal systems, your team's conventions, or your corporate environment. Once a workflow touches any of those, a custom plugin is the right call.

## What public marketplace skills are good for

- Generic tasks: write tests, explain code, summarize a PR
- Workflows that need no knowledge of your specific environment or data

## Why `dbt-schema-enrichment` had to be custom

### 1. Internal data access

The skill runs `dbt show --inline` against your actual Databricks Unity Catalog. It knows your catalog name, queries your `information_schema`, and reads real sample values from your tables. A public skill has no way to connect to your environment.

### 2. Domain-specific schema resolution

Databricks Unity Catalog nests `information_schema` directly under the catalog (`catalog.information_schema.columns`), not under a user schema. The skill was built specifically for this structure. A generic skill would assume a different layout and fail silently.

### 3. Corporate environment constraints

- TLS restrictions prevent using package managers like `uv` — the skill uses `pip` with `requirements.txt` instead
- Databricks CLI v1.14.1 is a standalone Go binary, not a pip package — the skill treats it as a prerequisite rather than a dependency
- `dbt show --inline` is used instead of the Databricks SQL API because the CLI's SQL subcommand is not available in this version

### 4. Opinionated team conventions

The skill encodes decisions specific to this team:
- `schema.yml` lives alongside the model file, not in a central location
- Descriptions are non-destructive: existing descriptions, tests, tags, and meta fields are never overwritten
- Schema is resolved dynamically from `information_schema.tables`, not assumed from config

None of these are universal — they are this team's choices.

## The tradeoff

Building and maintaining a custom plugin has real overhead: version bumps, a hosted marketplace repo, and keeping skills in sync with tooling changes. If a public skill already does what you need, use it. The custom plugin is justified here because the workflow is tightly coupled to internal systems and team conventions that a public skill cannot know.

## When to build custom vs use existing

| Situation | Recommendation |
|---|---|
| Generic task (write tests, explain code) | Use a marketplace skill |
| Workflow touches internal systems or data | Build custom |
| Team has strong conventions a public skill would violate | Build custom |
| Corporate environment with non-standard tooling | Build custom |
| Task is unique to your domain or data model | Build custom |

## Things to be aware of before wider rollout

### Plugins have an always-on context cost

Every installed plugin's skill names and descriptions load into Claude's context on every turn, even in sessions where the skill never runs — this is how Claude knows the skill exists at all. `disable-model-invocation: true` (used here) stops the skill from being auto-triggered, but the name/description still costs a small number of tokens per turn once installed.

### Plugins run with the user's own permissions — no sandboxing

Anything the plugin's scripts do (shell out to `dbt`, read/write files) runs as the installing user, exactly as if they had typed the command themselves. There is no sandbox. This is reasonable for an internal, team-authored plugin, but should be stated explicitly when rolling out to a wider audience.

### Updates are not automatic

Installing a plugin caches a specific version locally. Pushing a new commit does nothing for existing users until they explicitly run `claude plugin update`. This makes consistent version bumps (this plugin went 0.1.3 → 0.1.7 while fixing the Databricks query issues) the actual signal users rely on to know something changed.

### Install scope matters for team rollout

Three scopes are available: **user** (every project on that person's machine), **project** (enabled via committed `.claude/settings.json`, but each person still installs it locally), and **local** (just one repo, one user). For a tool meant to be used across many dbt projects, user scope is the right default — project scope would require installing it per-repo.

### Validation checks structure, not runtime behavior

`claude plugin validate --strict` catches manifest errors (missing fields, bad JSON, naming violations) before every push. It does not catch runtime bugs — for example, it would not have caught the nested-`LIMIT` SQL syntax error found during development. Validation is necessary before shipping a version bump, but not sufficient.

### There's a distribution ladder beyond a private marketplace

A private marketplace (what this repo is) is one tier of distribution. If adoption grows past the immediate team, Anthropic also runs an official plugin directory with its own submission process. Moving from "private marketplace for us" to "listed in Anthropic's directory" is a deliberate step, not something that happens automatically.
