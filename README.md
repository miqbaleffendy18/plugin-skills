# zurich-data-team Claude Plugin

Internal dbt tooling skills for the Zurich data team.

## Skills

### User-invoked

| Skill | Command | Description |
|---|---|---|
| dbt Schema Enrichment | `/zurich-data-team:dbt-schema-enrichment` | Enrich a dbt model's schema.yml with AI-generated column descriptions from Databricks |

## Installation

Add this repository as a plugin source in your Claude Code settings. Team members can install it via the internal marketplace by pointing to this GitHub repository.

## Prerequisites

- `uv` installed (`pip install uv` or `brew install uv`)
- `databricks` CLI configured (`~/.databrickscfg`)
- dbt project with `~/.dbt/profiles.yml` pointing at Databricks

## Documentation

- [dbt Schema Enrichment](docs/dbt-schema-enrichment.md)
- [Contributing](docs/contributing.md)
