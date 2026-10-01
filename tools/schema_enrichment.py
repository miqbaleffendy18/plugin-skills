#!/usr/bin/env python3
"""CLI entry point for dbt schema enrichment.

Commands:
  fetch     -- query Databricks for column metadata and write a manifest JSON
  populate  -- read the manifest JSON and surgically update schema.yml

Run with: uv run schema_enrichment.py <command> <model_name> --model-path <path>
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the tools directory is on the path so connections/ is importable
sys.path.insert(0, str(Path(__file__).parent))

import click
from ruamel.yaml import YAML


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
def cli():
    pass


@cli.command()
@click.argument("model_name")
@click.option(
    "--model-path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Absolute path to the model's .sql file.",
)
@click.option(
    "--no-samples",
    is_flag=True,
    default=False,
    help="Skip fetching sample rows (use when the model is not yet materialized).",
)
def fetch(model_name: str, model_path: Path, no_samples: bool):
    """Fetch column metadata from Databricks and write a manifest JSON."""
    from connections.dbt import find_project_root, get_default_target
    from connections.databricks import get_columns, get_samples

    model_dir = model_path.parent

    # Resolve dbt target
    project_root = find_project_root(model_path)
    target = get_default_target(project_root)
    catalog = target["catalog"]
    schema = target["schema"]
    warehouse_id = target["warehouse_id"]

    if not warehouse_id:
        click.echo(
            "ERROR: Could not determine the Databricks SQL warehouse ID from profiles.yml. "
            "Make sure 'http_path' is set under your default target.",
            err=True,
        )
        sys.exit(1)

    # Fetch columns
    click.echo(f"Fetching columns for {catalog}.{schema}.{model_name} ...")
    columns = get_columns(catalog, schema, model_name, warehouse_id)

    if not columns:
        click.echo(
            f"ERROR: Model '{model_name}' not found in {catalog}.{schema}.information_schema. "
            "Run 'dbt run -s {model_name}' to materialize it first, "
            "or re-run with --no-samples to generate descriptions from SQL alone.",
            err=True,
        )
        sys.exit(2)

    # Fetch samples
    samples_by_column: dict[str, list] = {}
    if not no_samples:
        click.echo("Fetching sample rows ...")
        try:
            rows = get_samples(catalog, schema, model_name, warehouse_id, limit=5)
            for col in columns:
                samples_by_column[col["name"]] = [
                    row.get(col["name"]) for row in rows
                ]
        except Exception as exc:
            click.echo(f"Warning: Could not fetch samples ({exc}). Continuing without them.", err=True)

    # Build manifest
    manifest = {
        "model": model_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "columns": [
            {
                "name": col["name"],
                "data_type": col["data_type"],
                "description": "",
                "samples": samples_by_column.get(col["name"], []),
            }
            for col in columns
        ],
    }

    manifest_path = model_dir / f"{model_name}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))

    click.echo(f"Manifest written to {manifest_path}")
    click.echo(f"Found {len(columns)} columns.")


@cli.command()
@click.argument("model_name")
@click.option(
    "--model-path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Absolute path to the model's .sql file.",
)
def populate(model_name: str, model_path: Path):
    """Read the manifest JSON and surgically update schema.yml."""
    model_dir = model_path.parent
    manifest_path = model_dir / f"{model_name}_manifest.json"
    schema_yml_path = model_dir / "schema.yml"

    if not manifest_path.exists():
        click.echo(
            f"ERROR: Manifest not found at {manifest_path}. Run 'fetch' first.",
            err=True,
        )
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text())

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 120

    # Load or initialise schema.yml
    if schema_yml_path.exists():
        with open(schema_yml_path) as f:
            data = yaml.load(f) or {}
    else:
        data = {}

    data.setdefault("version", 2)
    data.setdefault("models", [])

    # Find or create the model entry
    model_entry = next(
        (m for m in data["models"] if m.get("name") == model_name), None
    )
    if model_entry is None:
        model_entry = {"name": model_name, "description": "", "columns": []}
        data["models"].append(model_entry)

    model_entry.setdefault("columns", [])

    # Index existing columns by name for O(1) lookup
    existing: dict[str, dict] = {
        col["name"]: col for col in model_entry["columns"]
    }

    enriched = 0
    for manifest_col in manifest["columns"]:
        col_name = manifest_col["name"]
        description = manifest_col.get("description", "")

        if col_name in existing:
            if not existing[col_name].get("description"):
                existing[col_name]["description"] = description
                enriched += 1
        else:
            new_col = {"name": col_name, "description": description}
            model_entry["columns"].append(new_col)
            existing[col_name] = new_col
            enriched += 1

    with open(schema_yml_path, "w") as f:
        yaml.dump(data, f)

    click.echo(f"Updated {schema_yml_path}: {enriched} column(s) enriched.")


if __name__ == "__main__":
    cli()
