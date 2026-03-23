# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_wrangles.py

# Run a single test by name
pytest tests/test_wrangles.py::test_classify

# Run connector tests
pytest tests/connectors/test_postgres.py

# Run the CLI
wrangles.recipe recipe.wrgl.yml
wrangles.recipe recipe.wrgl.yml --functions custom.py --variables vars.py

# Regenerate JSON schema (after adding/modifying _schema dicts)
cd schema && python generate_recipe_schema.py
```

Tests require `WRANGLES_USER` and `WRANGLES_PASSWORD` env vars for cloud ML features. Connector tests may require additional credentials (AWS, Postgres, etc.).

## Architecture

### Recipe Execution Pipeline

The core abstraction is a **YAML recipe** that describes a data pipeline:

```yaml
read:      # Load data from sources (connectors)
wrangles:  # Apply transformations (wrangles)
write:     # Output results (connectors)
run:       # Lifecycle hooks: on_start, on_success, on_failure
```

`wrangles/recipe.py` drives the full execution:
1. `_load_recipe()` — parses YAML (file/URL/model ID/string/dict), performs `${VAR}` substitution with env vars and passed variables, loads custom functions
2. `_read_data()` — resolves connectors from the `read` section
3. `_execute_wrangles()` — iterates wrangles, expands wildcard columns, evaluates `if` conditionals, applies `where` row filtering, dispatches to the correct function, merges results back
4. `_write_data()` — resolves connectors from the `write` section
5. Runs in a `ThreadPoolExecutor` to support `timeout`

### Wrangles (Transformations)

Located in `wrangles/recipe_wrangles/`. Each wrangle is a function:

```python
def my_wrangle(df, input, output, **kwargs):
    # transforms df and returns it
    return df
```

Submodules: `main`, `convert`, `create`, `extract`, `format`, `merge`, `select`, `split`, `compare`, `generate`, `compute`, `pandas`.

In recipes, wrangles are referenced as `module.function` (e.g. `convert.case`, `select.columns`) or just `function` for top-level wrangles in `main.py`. The prefix `pandas.` calls pandas methods directly. The prefix `custom.` calls user-provided functions.

Functions can opt-in to special parameters by including them in their signature — `recipe.py` injects them automatically via `utils.add_special_parameters()`: `df`, `functions`, `variables`, `error`.

### Connectors

Located in `wrangles/connectors/`. Each connector module exposes `read(...)`, `write(df, ...)`, and/or `run(...)` functions. In recipes, the connector name matches the module name (e.g. `file`, `postgres`, `s3`, `sftp`).

Classes within a connector (e.g. `sftp.download_files`) are exposed as `connector.class_name` in recipes and must implement a `run()` static method.

### Schema System

Every wrangle and connector module defines `_schema` — a dict of YAML strings (JSON Schema format) keyed by `'read'`, `'write'`, `'run'`, or wrangle name. These are used for recipe validation and IDE autocomplete. When adding a new parameter to a function, also add it to its `_schema` entry. The schema is compiled into `schema/schema.json` by `schema/generate_recipe_schema.py`.

### LazyLoader

Optional heavy dependencies (paramiko, pymongo, boto3, etc.) are loaded via `utils.LazyLoader`:

```python
_boto3 = _LazyLoader('boto3')
# Only imported when first attribute is accessed
```

### Column Wildcards

`utils.wildcard_expansion()` expands patterns in wrangle `input` fields:
- `*` matches any substring
- `:regex:pattern` uses regex
- `:2:5` slices column list by index

### DataFrame Fluent API

`wrangles/dataframe.py` registers a `.wrangles` accessor on pandas DataFrames, allowing method-chained wrangle calls:

```python
df.wrangles.filter(...).wrangles.convert.case(...)
```

### Authentication

Cloud ML features (classify, extract, standardize, translate) require WrangleWorks credentials. Set via env vars `WRANGLES_USER` / `WRANGLES_PASSWORD`, or call `wrangles.authenticate(user, password)` at runtime. Config lives in `wrangles/config.py`.
