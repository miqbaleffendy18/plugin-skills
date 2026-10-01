# dbt Schema Enrichment

## What it does

Enriches a dbt model's `schema.yml` with AI-generated column descriptions. The skill:

1. Queries Databricks `information_schema` for the model's column names and data types
2. Fetches 5 sample rows to give AI context about real values
3. Reads the model's SQL to understand how columns are computed
4. Generates a concise one-sentence description for each column
5. Writes the descriptions back to `schema.yml` -- only empty descriptions are filled; nothing else is touched

## When to reach for it

- You have a new or under-documented dbt model with no column descriptions
- You want to bulk-fill descriptions without manually writing each one
- You want descriptions that reflect actual data values, not just column names

## Usage

```
/zurich-data-team:dbt-schema-enrichment <model_name>
```

Example:

```
/zurich-data-team:dbt-schema-enrichment dim_customers
```

If you do not provide a model name, the skill will ask for one.

## Prerequisites

- dbt 1.5+ installed and configured (`dbt_project.yml` + `profiles.yml` pointing at Databricks)
- Python 3.11 venv with `tools/requirements.txt` installed
- The model must already be materialized in Databricks (i.e. `dbt run -s <model>` has been run)

## Setup

Activate your Python 3.11 venv, then install the dependencies:

```bash
pip install -r tools/requirements.txt
```

> **Corporate TLS note**: If `pip install` fails with a certificate error, add your company's CA bundle:
> ```bash
> pip install --cert /path/to/company-ca-bundle.crt -r tools/requirements.txt
> ```

## What the skill will NOT change

- Existing column descriptions (already-written descriptions are never overwritten)
- Column tests, tags, or meta fields
- Column order in `schema.yml`
- Other models in the same `schema.yml` file
- Any YAML comments

## Files written

| File | Description |
|---|---|
| `schema.yml` | Updated in place (or created if missing) |
| `<model_name>_manifest.json` | Intermediate manifest left for inspection; safe to delete; add `*_manifest.json` to `.gitignore` |

## It's working if

- The skill prints "X column(s) enriched" at the end
- `schema.yml` now has non-empty `description` fields under the model's columns
- Columns that already had descriptions are unchanged

## Common issues

**"Model not found in information_schema"** -- The model has not been materialized in your dev environment. Run `dbt run -s <model_name>` first. The skill will offer to generate descriptions from SQL logic alone if you cannot run the model.

**"dbt show failed"** -- Check that `dbt debug` passes in your project directory. The `dbt show --inline` command requires dbt 1.5+.

**"profiles.yml not found"** -- Make sure `profiles.yml` exists (default: `~/.dbt/profiles.yml`) and your profile is configured for Databricks. Use `--profiles-dir` if it lives in a custom location.
