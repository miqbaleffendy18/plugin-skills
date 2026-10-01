"""Utilities for reading dbt project configuration."""

from __future__ import annotations

from pathlib import Path

import yaml


def find_project_root(start: Path) -> Path:
    """Walk up from start until dbt_project.yml is found."""
    current = start if start.is_dir() else start.parent
    for directory in [current, *current.parents]:
        if (directory / "dbt_project.yml").exists():
            return directory
    raise FileNotFoundError(
        f"Could not find dbt_project.yml walking up from {start}. "
        "Make sure you are inside a dbt project."
    )


def get_default_target(project_root: Path, profiles_dir: Path | None = None) -> dict:
    """Return catalog, schema, http_path, and host for the default dbt target.

    Reads dbt_project.yml for the profile name, then reads profiles.yml
    for the default target's Databricks connection details.

    profiles_dir resolution order (mirrors dbt's own logic):
      1. profiles_dir argument if provided
      2. DBT_PROFILES_DIR environment variable
      3. ~/.dbt/
    """
    import os

    dbt_project = _load_yaml(project_root / "dbt_project.yml")
    profile_name = dbt_project.get("profile")
    if not profile_name:
        raise ValueError("dbt_project.yml is missing a 'profile' key.")

    if profiles_dir is None:
        env_dir = os.environ.get("DBT_PROFILES_DIR")
        profiles_dir = Path(env_dir) if env_dir else Path.home() / ".dbt"

    profiles_path = profiles_dir / "profiles.yml"
    if not profiles_path.exists():
        raise FileNotFoundError(f"profiles.yml not found at {profiles_path}.")

    profiles = _load_yaml(profiles_path)
    profile = profiles.get(profile_name)
    if not profile:
        raise ValueError(
            f"Profile '{profile_name}' not found in {profiles_path}."
        )

    target_name = profile.get("target")
    if not target_name:
        raise ValueError(f"Profile '{profile_name}' has no 'target' key.")

    outputs = profile.get("outputs", {})
    target = outputs.get(target_name)
    if not target:
        raise ValueError(
            f"Target '{target_name}' not found under profile '{profile_name}'."
        )

    return {
        "catalog": target.get("catalog", ""),
        "schema": target.get("schema", ""),
    }


def get_model_schema(project_root: Path, model_path: Path) -> str:
    """Resolve the Databricks schema for a model from dbt_project.yml +schema configs.

    Walks the models config from the most specific subdirectory to the least,
    returning the first +schema value found. Falls back to an empty string.

    Example: a model at src/models/staging/dim_customers.sql resolves to the
    +schema set under models.<project_name>.staging in dbt_project.yml.
    """
    dbt_project = _load_yaml(project_root / "dbt_project.yml")
    project_name = dbt_project.get("name", "")
    model_dirs = dbt_project.get("model-paths", ["models"])

    rel_parts: list[str] | None = None
    for model_base in model_dirs:
        base_path = project_root / model_base
        try:
            rel_path = model_path.relative_to(base_path)
            rel_parts = list(rel_path.parts[:-1])  # exclude the filename
            break
        except ValueError:
            continue

    if not rel_parts:
        return ""

    project_models_config = dbt_project.get("models", {}).get(project_name, {})

    # Try most-specific path first, progressively less specific
    for depth in range(len(rel_parts), 0, -1):
        config = project_models_config
        for part in rel_parts[:depth]:
            config = config.get(part, {})
            if not isinstance(config, dict):
                config = {}
                break
        schema = config.get("+schema")
        if schema:
            return schema

    return ""


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}
