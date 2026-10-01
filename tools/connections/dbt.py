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


def get_default_target(project_root: Path) -> dict:
    """Return catalog, schema, http_path, and host for the default dbt target.

    Reads dbt_project.yml for the profile name, then reads ~/.dbt/profiles.yml
    for the default target's Databricks connection details.
    """
    dbt_project = _load_yaml(project_root / "dbt_project.yml")
    profile_name = dbt_project.get("profile")
    if not profile_name:
        raise ValueError("dbt_project.yml is missing a 'profile' key.")

    profiles_path = Path.home() / ".dbt" / "profiles.yml"
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

    http_path = target.get("http_path", "")
    warehouse_id = http_path.rstrip("/").split("/")[-1] if http_path else ""

    return {
        "catalog": target.get("catalog", ""),
        "schema": target.get("schema", ""),
        "host": target.get("host", ""),
        "http_path": http_path,
        "warehouse_id": warehouse_id,
    }


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}
