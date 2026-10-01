"""Utilities for querying Databricks via the Databricks CLI.

Requires the Databricks CLI (v0.200+) installed and configured in ~/.databrickscfg.
"""

from __future__ import annotations

import json
import subprocess


def get_columns(
    catalog: str,
    schema: str,
    table: str,
    warehouse_id: str,
) -> list[dict]:
    """Return a list of {name, data_type} dicts for the given table.

    Returns an empty list if the table does not exist in information_schema.
    """
    sql = (
        f"SELECT column_name, data_type "
        f"FROM {catalog}.information_schema.columns "
        f"WHERE table_schema = '{schema}' AND table_name = '{table}' "
        f"ORDER BY ordinal_position"
    )
    rows, _ = _execute(sql, warehouse_id)
    return [{"name": row[0], "data_type": row[1]} for row in rows]


def get_samples(
    catalog: str,
    schema: str,
    table: str,
    warehouse_id: str,
    limit: int = 5,
) -> list[dict]:
    """Return up to `limit` rows from the table as a list of column->value dicts."""
    sql = f"SELECT * FROM {catalog}.{schema}.{table} LIMIT {limit}"
    rows, col_names = _execute(sql, warehouse_id)
    return [dict(zip(col_names, row)) for row in rows]


def _execute(sql: str, warehouse_id: str) -> tuple[list[list], list[str]]:
    """Run SQL via the Databricks CLI and return (rows, column_names)."""
    result = subprocess.run(
        [
            "databricks", "sql", "statements", "execute",
            "--statement", sql,
            "--warehouse-id", warehouse_id,
            "--wait-timeout", "50s",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Databricks CLI error: {result.stderr.strip() or result.stdout.strip()}"
        )

    data = json.loads(result.stdout)

    state = data.get("status", {}).get("state", "")
    if state != "SUCCEEDED":
        error = data.get("status", {}).get("error", {})
        raise RuntimeError(
            f"Query failed ({state}): {error.get('message', 'unknown error')}"
        )

    rows = data.get("result", {}).get("data_array") or []
    col_names = [
        col["name"]
        for col in data.get("manifest", {}).get("schema", {}).get("columns", [])
    ]

    return rows, col_names
