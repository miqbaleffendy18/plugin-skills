# Contributing

## Adding a new skill

1. Create a directory under `skills/`:

   ```
   skills/<skill-name>/
   ├── SKILL.md
   └── agents/
       └── openai.yaml
   ```

2. Write `SKILL.md` with this frontmatter:

   ```yaml
   ---
   name: <skill-name>
   description: <plain human summary -- no trigger phrases>
   disable-model-invocation: true
   ---
   ```

   Keep the description factual. Trigger phrases (for model-invoked skills) are not used here since all skills in this plugin are user-invoked.

3. Write `agents/openai.yaml`:

   ```yaml
   interface:
     display_name: "<Human-readable name>"
     short_description: "<One-line description>"

   policy:
     allow_implicit_invocation: false
   ```

4. Register the skill in `.claude-plugin/plugin.json` by adding its path to the `skills` array:

   ```json
   "skills": [
     "./skills/dbt-schema-enrichment",
     "./skills/<your-new-skill>"
   ]
   ```

5. Add a docs page at `docs/<skill-name>.md` (see [dbt-schema-enrichment.md](dbt-schema-enrichment.md) as a template).

6. Add the skill to `README.md`.

7. Validate the plugin:

   ```bash
   claude plugin validate . --strict
   ```

---

## Adding a shared tool or connection

If your skill needs a reusable Python utility, add it under `tools/connections/`. The `tools/` directory is a uv project -- add any new dependencies to `tools/pyproject.toml`.

For a skill-specific script (like `schema_enrichment.py`), name it after the skill and place it directly under `tools/`.

---

## Updating the plugin version

The version number lives in two files that must stay in sync:

| File | Key |
|---|---|
| `package.json` | `"version"` |
| `.claude-plugin/plugin.json` | `"version"` |

Steps to release a new version:

1. Decide the new version number following [semver](https://semver.org/):
   - **Patch** (`0.1.0` -> `0.1.1`): bug fixes, wording improvements in skill instructions
   - **Minor** (`0.1.0` -> `0.2.0`): new skill added, new CLI command, non-breaking changes
   - **Major** (`0.1.0` -> `1.0.0`): breaking change to skill interface or tool CLI contract

2. Update `package.json`:

   ```json
   { "version": "0.2.0" }
   ```

3. Update `.claude-plugin/plugin.json`:

   ```json
   { "version": "0.2.0" }
   ```

4. Validate:

   ```bash
   claude plugin validate . --strict
   ```

5. Commit, tag, and push:

   ```bash
   git add package.json .claude-plugin/plugin.json
   git commit -m "chore: bump version to 0.2.0"
   git tag v0.2.0
   git push origin main --tags
   ```

6. Team members update by pulling the latest tag from the marketplace.
