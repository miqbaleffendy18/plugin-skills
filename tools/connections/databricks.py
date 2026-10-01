"""Utilities for querying Databricks via the SDK.

Authentication is read from ~/.databrickscfg (PAT profile).
The SQL warehouse is provided by the caller (resolved from dbt profiles.yml).
"""

from __future__ import annotations

import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState


def get_columns(
    catalog: str,
    schema: str,
    table: str,
    warehouse_id: str,
) -> list[dict]:
    """Return a list of {name, data_type} dicts for the given table.

    Returns an empty list if the table does not exist in information_schema.
    """
    sql = f"""
        SELECT column_name, data_type
        FROM {catalog}.information_schema.columns
        WHERE table_schema = '{schema}'
          AND table_name   = '{table}'
        ORDER BY ordinal_position
    """
    rows = _execute(sql, warehouse_id, catalog, schema)
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
    rows = _execute(sql, warehouse_id, catalog, schema)

    # Fetch column names via information_schema to build the dicts
    cols = get_columns(catalog, schema, table, warehouse_id)
    col_names = [c["name"] for c in cols]

    return [dict(zip(col_names, row)) for row in rows]


def _execute(
    sql: str,
    warehouse_id: str,
    catalog: str | None = None,
    schema: str | None = None,
) -> list[list]:
    """Run a SQL statement and return rows as a list of lists."""
    client = WorkspaceClient()

    kwargs: dict = {"statement": sql, "warehouse_id": warehouse_id}
    if catalog:
        kwargs["catalog"] = catalog
    if schema:
        kwargs["schema"] = schema

    response = client.statement_execution.execute_statement(**kwargs)

    # Poll until terminal state
    statement_id = response.statement_id
    for _ in range(60):
        if response.status.state in (
            StatementState.SUCCEEDED,
            StatementState.FAILED,
            StatementState.CANCELED,
            StatementState.CLOSED,
        ):
            break
        time.sleep(2)
        response = client.statement_execution.get_statement(statement_id)

    if response.status.state != StatementState.SUCCEEDED:
        error = response.status.error
        raise RuntimeError(
            f"Databricks query failed ({response.status.state}): "
            f"{error.message if error else 'unknown error'}"
        )

    result = response.result
    if not result or not result.data_array:
        return []
    return result.data_array
