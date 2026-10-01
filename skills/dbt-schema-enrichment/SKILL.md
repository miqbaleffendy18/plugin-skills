---
name: dbt-schema-enrichment
description: Enrich a dbt model's schema.yml with AI-generated column descriptions pulled from Databricks.
disable-model-invocation: true
---

## Overview

Enriches a dbt model's `schema.yml` with column descriptions. The skill fetches column metadata and sample data from Databricks, uses AI to write concise descriptions, and writes them back non-destructively -- only empty descriptions are filled; existing descriptions, tests, tags, and meta fields are never touched.

## Prerequisites

- Python venv with `tools/requirements.txt` installed and activated
- dbt 1.5+ installed and configured with `dbt_project.yml` and `profiles.yml` pointing at Databricks

## Locating the tools script

This SKILL.md is loaded from `skills/dbt-schema-enrichment/` inside the plugin root. The tools script is two levels up from this skill directory:

```
<skill_base_dir>/../../tools/schema_enrichment.py
```

Resolve this to a normalized absolute path before running any commands. For example, if the skill base directory is `/home/user/.claude/plugins/cache/zurich-data-team/0.1.3/skills/dbt-schema-enrichment`, the tools script is at `/home/user/.claude/plugins/cache/zurich-data-team/0.1.3/tools/schema_enrichment.py`.

Store this resolved path as `TOOLS_SCRIPT` for use throughout the steps below.

## Steps

### 1. Get the model name

If the user did not provide a model name, ask: "Which dbt model would you like to enrich?"

### 2. Find the model file

Search the current working directory recursively for `<model_name>.sql` under a `models/` directory.

```bash
find . -path "*/models/**/<model_name>.sql" -type f
```

If not found, tell the user and stop.

Store the resolved absolute path as `MODEL_PATH`. The directory containing it is `MODEL_DIR`.

### 3. Fetch column metadata from Databricks

Run:

```bash
python "$TOOLS_SCRIPT" fetch <model_name> --model-path "$MODEL_PATH"
```

If `profiles.yml` is not in `~/.dbt/`, pass `--profiles-dir` pointing to its directory:

```bash
python "$TOOLS_SCRIPT" fetch <model_name> --model-path "$MODEL_PATH" --profiles-dir "<profiles_dir>"
```

The flag also respects the `DBT_PROFILES_DIR` environment variable automatically if set.

This script:
- Walks up from `MODEL_PATH` to find `dbt_project.yml` (the dbt project root)
- Reads `dbt_project.yml` and `profiles.yml` to resolve the default target's catalog
- Runs `dbt show --inline` to query `information_schema.columns` for column names and data types (schema is resolved automatically from `information_schema.tables`)
- Runs `dbt show --inline` to fetch 5 sample rows from the materialized table
- Writes `<model_name>_manifest.json` in `MODEL_DIR`

**If the script exits with a non-zero code and the error mentions the model is not found in Databricks:**

Ask the user: "The model `<model_name>` was not found in Databricks. It may not have been materialized yet. Would you like to generate descriptions from the SQL query logic alone, without sample data? (yes/no)"

- If yes: re-run with `--no-samples`
- If no: stop and tell the user to run `dbt run -s <model_name>` first

### 4. Read the manifest and the model SQL

Read both files:
- `MODEL_DIR/<model_name>_manifest.json`
- `MODEL_PATH` (the `.sql` file)

### 5. Generate column descriptions

For every column in the manifest where `description` is an empty string (`""`):

Use the following to write a clear, concise one-sentence description:
- The column `name` and `data_type`
- The `samples` array (if present -- values reveal semantic meaning that names alone cannot)
- The SQL query logic from the model file (CTEs, joins, and expressions show how the column is computed)

Rules:
- One sentence per description, no trailing period needed
- Be specific: prefer "Customer's ISO 3166-1 alpha-2 country code" over "Country of the customer"
- Do not invent meaning that cannot be inferred from the above sources

Write all generated descriptions back into the manifest JSON, replacing the empty strings. Write the updated file to the same path.

### 6. Populate schema.yml

Run:

```bash
python "$TOOLS_SCRIPT" populate <model_name> --model-path "$MODEL_PATH"
```

This script reads the manifest and surgically updates `MODEL_DIR/schema.yml`:
- Creates `schema.yml` from scratch if it does not exist
- Creates the model entry if not already present
- For each column: adds a new entry if missing, fills description only if currently empty
- Preserves all existing tests, tags, meta fields, and column order

### 7. Confirm

Tell the user:
- How many columns were enriched
- The path to the updated `schema.yml`
- That the manifest file (`<model_name>_manifest.json`) was left in place for inspection and is safe to delete or `.gitignore`
