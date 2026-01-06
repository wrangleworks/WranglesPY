# Copilot Instructions for WranglesPY

## Overview
WranglesPY is a Python package for data wrangling and transformation. It provides modular transformations for data cleaning and enrichment, backed by machine learning models. The package supports both direct function calls and YAML-based recipe execution for automated data workflows.

**Repository Size:** ~17,000 lines of Python code  
**Language:** Python  
**Supported Versions:** Python 3.10, 3.11, 3.12, 3.13  
**Package Manager:** pip  
**Testing Framework:** pytest 7.4.4

## Key Dependencies
- pandas >= 2.0, < 3.0
- numpy
- polars == 1.33.0
- openpyxl >= 3.1.0
- sqlalchemy >= 2.0, < 3.0
- Database connectors: pymssql, psycopg2-binary, pymysql, pymongo
- Cloud: boto3, simple-salesforce
- Other: pyyaml, pydantic, fabric, apprise, jinja2

## Build & Installation Commands

### Initial Setup (ALWAYS run in this order)
1. **Upgrade pip first:**
   ```bash
   python -m pip install --upgrade pip
   ```

2. **Install test dependencies:**
   ```bash
   pip install pytest==7.4.4 lorem pytest-mock
   ```

3. **Install project dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   Time: ~30-60 seconds. Large dependencies include polars (~39 MB) and pandas (~12 MB).

4. **Install package in development mode (optional):**
   ```bash
   pip install .
   ```
   Time: ~20-30 seconds.

### macOS-Specific Setup
On macOS-latest (x86), you MUST install FreeTDS before pip install:
```bash
brew update
brew install freetds
```
This is required for pymssql to work properly.

### Testing the Installation
After installing the package (step 4 above), verify with:
```bash
wrangles.recipe tests/samples/generate-data.wrgl.yml
```
Expected: Should execute successfully and display a 5-row dataframe.
Note: This command requires the package to be installed (`pip install .`) to work.

## Testing

### Running Tests
```bash
pytest
```
- **All tests:** pytest (discovers tests from `tests/` directory)
- **Single test:** pytest tests/test_wrangles.py::test_function_name -v
- **Test discovery:** pytest --collect-only

### Test Structure
Total: over 1600 tests across all files (use `pytest --collect-only` to see current count).

- `tests/test_wrangles.py` - Core wrangles functionality (primary test file)
- `tests/test_back_processes.py` - Authentication and backend processes
- `tests/recipes/` - Recipe-related tests
  - `test_read.py`, `test_write.py` - Connector tests
  - `test_recipes.py`, `test_run.py` - Recipe execution
  - `wrangles/` - Individual wrangle tests (extract, format, convert, etc.)
- `tests/connectors/` - Connector-specific tests
- `tests/samples/` - Sample data files and recipes for testing

### Authentication for Tests
Many tests require API credentials set as environment variables:
- `WRANGLES_USER`
- `WRANGLES_PASSWORD`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- `HUGGINGFACE_TOKEN`
- `OPENAI_API_KEY`

Tests will fail with "User or password not provided" if credentials are missing. This is expected in local development.

## Project Structure

### Core Directories
- **`wrangles/`** - Main package code
  - `__init__.py` - Package exports (classify, extract, lookup, translate, etc.)
  - `recipe.py` - Recipe execution engine (large, complex file)
  - `extract.py`, `format.py`, `generate.py`, etc. - Wrangle functions
  - `auth.py`, `config.py` - Authentication and configuration
  - `connectors/` - Data source connectors (file, database, cloud, APIs)
  - `recipe_wrangles/` - Recipe-specific wrangle implementations
- **`tests/`** - All test files
- **`schema/`** - JSON schema generation for recipe validation
  - `generate_recipe_schema.py` - Schema generator
  - `recipe_base_schema.json` - Base schema definition
- **`setup.py`** - Package configuration and metadata
- **`requirements.txt`** - Dependencies
- **`dockerfile`** - Docker container definition

### Key Files in Root
- `README.md` - User documentation
- `main.py` - Docker entrypoint for running recipes
- `.coveragerc` - Test coverage configuration
- `setup.cfg` - Metadata configuration
- `.devcontainer/devcontainer.json` - VS Code dev container setup

## GitHub Actions CI/CD

### Workflows
1. **`.github/workflows/publish-main.yml`** (Push to main/PRs to main):
   - Runs on: ubuntu-latest, windows-latest, macos-14, macos-latest
   - Matrix: Python 3.10, 3.11, 3.12, 3.13
   - Jobs:
     - `pytest` - Run all tests with credentials
     - `test-pip-install` - Test package installation
     - `test-generate-schema` - Generate and validate schema (Python 3.12, Ubuntu only)
     - `build` - Build and push Docker image to ghcr.io
     - `test-container` - Test Docker container with recipes

2. **`.github/workflows/publish-dev.yml`** (Push to dev/PRs to dev):
   - Simplified version, runs on Ubuntu with Python 3.10 only
   - Same job structure but fewer matrix combinations

3. **`.github/workflows/publish-tagged.yml`** (Tagged releases):
   - Includes PyPI deployment steps
   - Publishes to test.pypi.org first, then pypi.org

### CI Requirements for PR Success
All PRs to main MUST pass:
1. pytest on all OS/Python combinations (may take 10+ minutes per matrix job)
2. pip install test on all OS/Python combinations
3. Schema generation validation (Ubuntu, Python 3.12)

### macOS CI Note
The workflows have separate jobs for macos-latest with FreeTDS installation. This is because pymssql requires FreeTDS on macOS.

## Common Issues and Workarounds

### 1. Authentication Errors in Tests
**Error:** `RuntimeError: User or password not provided`  
**Cause:** Tests requiring API access but credentials not set  
**Solution:** This is expected behavior without credentials. Skip these tests or set required environment variables.

### 2. Build Artifacts
The `build/` directory is created during `pip install .` and contains compiled package files. It's in `.gitignore` and should not be committed.

### 3. Schema Generation Network Issues
`schema/generate_recipe_schema.py` may fail with network errors when validating against remote JSON schema. This is a known issue and doesn't affect core functionality.

### 4. Test Data Directory
`tests/temp/` is used for temporary test files. Only `tests/temp/README.md` should be committed (see `.gitignore`).

## Coding Patterns

### Recipe Files
- Extension: `.wrgl.yml`, `.wrgl.yaml`, or `.recipe`
- Structure: YAML with `read`, `wrangles`, and `write` sections
- Schema: https://public.wrangle.works/schema/recipes/schema.json

### Connectors
- Located in `wrangles/connectors/`
- Implement `_schema` attribute with YAML documentation for read/write/run
- Support both reading (returns DataFrame) and writing (accepts DataFrame)

### Recipe Wrangles
- Located in `wrangles/recipe_wrangles/`
- Main entry point: `main.py` contains all recipe-callable wrangles (large, comprehensive file)

## DO NOT's
- Do NOT add linting tools (none configured)
- Do NOT run tests without first installing test dependencies
- Do NOT commit `build/`, `dist/`, `*.egg-info/`, or `__pycache__/` directories
- Do NOT commit `tests/temp/*` except README.md
- Do NOT attempt to fix tests that require credentials unless credentials are available

## Validation Steps

### Before Committing Code Changes
1. Install dependencies: `pip install -r requirements.txt`
2. Install test dependencies: `pip install pytest==7.4.4 lorem pytest-mock`
3. Test package installation: `pip install .`
4. Run relevant tests: `pytest tests/specific_test.py` (if applicable)
5. Test recipe execution: `wrangles.recipe tests/samples/generate-data.wrgl.yml`

### For Connector Changes
Test with sample recipes from `tests/samples/` directory.

### For Schema Changes
Run: `cd schema && python generate_recipe_schema.py` (may have network issues, non-critical)

## Trust These Instructions
These instructions have been validated by running actual commands in the repository. If information seems incomplete or incorrect, verify by testing the command yourself before searching extensively. Most common operations are documented here.
