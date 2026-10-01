"""Utilities for querying Databricks via dbt show --inline.

Uses the dbt project's existing profile connection -- no separate auth needed.
Requires dbt 1.5+ (for --inline support).
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def get_columns(
    catalog: str,
    table: str,
    project_root: Path,
    profiles_dir: Path | None = None,
) -> list[dict]:
    """Return a list of {name, data_type} dicts for the given table.

    Does not filter by schema -- matches table_name across all schemas in the
    catalog so schema name mismatches never cause false negatives.
    Returns an empty list if the table is not found.
    """
    sql = (
        f"SELECT column_name, data_type "
        f"FROM {catalog}.information_schema.columns "
        f"WHERE table_name = '{table}' "
        f"ORDER BY ordinal_position"
    )
    rows, headers = _dbt_show(sql, project_root, profiles_dir)
    if not rows:
        return []
    col_idx = headers.index("column_name")
    type_idx = headers.index("data_type")
    return [{"name": row[col_idx], "data_type": row[type_idx]} for row in rows]


def get_samples(
    catalog: str,
    table: str,
    project_root: Path,
    profiles_dir: Path | None = None,
    limit: int = 5,
) -> list[dict]:
    """Return up to `limit` rows from the table as a list of column->value dicts.

    Looks up the actual schema from information_schema.tables first so the
    SELECT uses the correct fully-qualified name regardless of dbt schema config.
    """
    schema = _resolve_schema(catalog, table, project_root, profiles_dir)
    if schema is None:
        raise RuntimeError(
            f"Table '{table}' not found in catalog '{catalog}'. "
            "Run 'dbt run' to materialize it first."
        )
    sql = f"SELECT * FROM {catalog}.{schema}.{table}"
    rows, headers = _dbt_show(sql, project_root, profiles_dir, limit=limit)
    return [dict(zip(headers, row)) for row in rows]


def _resolve_schema(
    catalog: str,
    table: str,
    project_root: Path,
    profiles_dir: Path | None = None,
) -> str | None:
    """Look up the actual schema a table lives in via information_schema.tables."""
    sql = (
        f"SELECT table_schema "
        f"FROM {catalog}.information_schema.tables "
        f"WHERE table_name = '{table}'"
    )
    rows, headers = _dbt_show(sql, project_root, profiles_dir, limit=1)
    if not rows:
        return None
    return rows[0][headers.index("table_schema")]


def _dbt_show(
    sql: str,
    project_root: Path,
    profiles_dir: Path | None = None,
    limit: int = 500,
) -> tuple[list[list[str]], list[str]]:
    """Run `dbt show --inline` and return (rows, column_names)."""
    cmd = ["dbt", "show", "--inline", sql, "--limit", str(limit)]
    if profiles_dir:
        cmd.extend(["--profiles-dir", str(profiles_dir)])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"dbt show failed:\n{result.stderr.strip() or result.stdout.strip()}"
        )

    return _parse_table(result.stdout)


def _parse_table(output: str) -> tuple[list[list[str]], list[str]]:
    """Parse the pipe-delimited table that dbt show writes to stdout."""
    table_lines = [
        line.strip()
        for line in output.splitlines()
        if line.strip().startswith("|")
    ]

    if not table_lines:
        return [], []

    def split_row(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip("|").split("|")]

    headers = split_row(table_lines[0])
    # table_lines[1] is the separator row (| --- | --- |), skip it
    rows = [split_row(line) for line in table_lines[2:]]

    return rows, headers
