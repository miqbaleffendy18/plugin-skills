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
