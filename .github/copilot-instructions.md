# WranglesPY - Copilot Instructions

## Project Overview

**WranglesPY** is a Python library for data wrangling, cleaning, and enrichment. It provides modular transformations (called "Wrangles") optimized for specific tasks, many backed by machine learning models. The library supports both programmatic use (as Python functions) and declarative use (via YAML recipes).

**Key Capabilities:**
- Extract information from messy descriptions
- Predict categories for items
- Standardize text data
- Move data between systems (ETL)
- System-independent data transformations

## Tech Stack

- **Python:** 3.11, 3.12, 3.13 (multi-version support)
- **Core Dependencies:** pandas (>=2.0), numpy, polars (1.33.0), pyyaml
- **Database Connectors:** sqlalchemy, pymssql, psycopg2-binary, pymysql, pymongo
- **Cloud/External:** boto3 (AWS S3), simple-salesforce, fabric (SFTP)
- **Data Formats:** openpyxl (Excel), xlsxwriter
- **AI/ML:** OpenAI integration, Hugging Face models
- **Testing:** pytest (9.0.2), pytest-mock, lorem (test data generation)
- **Containerization:** Production Docker image uses Python 3.11-slim-bookworm; development container uses Python 3.13-bookworm

## Project Structure

```
WranglesPY/
├── wrangles/                   # Main package
│   ├── __init__.py             # Public API exports
│   ├── recipe.py               # Recipe execution engine (~4800 lines)
│   ├── connectors/             # Data source/destination connectors
│   │   ├── README.md           # Connector implementation guidelines
│   │   └── *.py                # Individual connectors (salesforce, postgres, etc.)
│   ├── recipe_wrangles/        # Recipe-specific transformations
│   │   ├── extract.py          # Extract operations
│   │   ├── convert.py          # Convert operations
│   │   ├── merge.py, split.py, etc.
│   └── *.py                    # Core modules (extract, classify, standardize, etc.)
├── tests/                      # Test suite
│   ├── test_wrangles.py        # Main function tests
│   ├── connectors/             # Connector tests
│   ├── recipes/                # Recipe execution tests
│   │   └── wrangles/           # Individual wrangle tests
│   └── samples/                # Sample recipes and data files
│       ├── *.wrgl.yml          # Recipe files
│       └── custom_functions.py # Custom function examples
├── schema/                     # JSON schema generation
│   ├── generate_recipe_schema.py
│   └── recipe_base_schema.json
├── setup.py                    # Package setup (version: 1.16.0)
├── requirements.txt            # Production dependencies
├── dockerfile                  # Multi-stage Docker build
├── main.py                     # Container entry point
└── .github/workflows/          # CI/CD pipelines
```

## Installation & Setup

### Development Installation
```bash
pip install --upgrade pip
pip install pytest==9.0.2 pytest-mock
pip install -r requirements-full.txt
pip install -e .
```

### macOS-specific Requirements
On macOS, install FreeTDS before installing Python dependencies:
```bash
brew update
brew install freetds
pip install -r requirements.txt
```

### Development Container
The project includes a `.devcontainer/devcontainer.json` for VS Code:
- Base image: `mcr.microsoft.com/devcontainers/python:1-3.13-bookworm`
- Auto-installs the full test dependencies and the package in editable mode
- Includes YAML schema validation for `.wrgl.yml` and `.recipe` files
- Configured for pytest test discovery

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_wrangles.py

# Run specific test
pytest tests/test_wrangles.py::test_classify -v

# Run tests with coverage
pytest --cov=wrangles
```

### Test Structure
- **tests/test_wrangles.py:** Core function tests (classify, extract, etc.)
- **tests/connectors/:** Connector-specific tests
- **tests/recipes/:** Recipe execution and wrangle tests
- **tests/samples/:** Sample data files and recipes for testing

### Authentication for Tests
Some tests require cloud-based ML models and need credentials set as environment variables:
- `WRANGLES_USER` and `WRANGLES_PASSWORD`
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- `HUGGINGFACE_TOKEN`
- `OPENAI_API_KEY`

Tests that require authentication will fail without these variables but this is expected in local development.

## Building & Packaging

### Local Installation
```bash
pip install .
```

### Test Installation
```bash
pip install .
wrangles.recipe tests/samples/generate-data.wrgl.yml
```

### Docker Build
The Dockerfile uses multi-stage builds for optimization:
1. Compile stage: Installs build dependencies and packages
2. Build stage: Copies only necessary files (~400MB final image)
3. Special optimizations: Removes unused botocore AWS service definitions, pandas test data

```bash
docker build -t wrangles:latest .
```

## Coding Guidelines

### Code Style
- Follow existing patterns in the codebase (no formal linter configured)
- Use descriptive variable names
- Keep functions focused and modular
- Comment sparingly - only for complex logic or non-obvious behavior

### Module Organization
- **wrangles/*.py:** Core transformation functions (extract, classify, standardize, etc.)
- **wrangles/connectors/*.py:** Read/write connectors for external systems
- **wrangles/recipe_wrangles/*.py:** Recipe-specific wrangle implementations
- Each connector should have a `_schema` attribute for documentation

### Reserved Words
The codebase uses `reserved_word_replacements` in `wrangles/config.py` to handle YAML reserved words (e.g., `on` → `input`).

### Error Handling
- Raise `TypeError` for invalid input data types
- Raise `ValueError` for incorrect parameter formats or values
- Include clear, actionable error messages

### Testing Patterns
```python
# Standard test pattern
def test_function_name():
    result = wrangles.function('input')
    assert result == expected_value

# Error testing pattern
def test_function_error():
    with pytest.raises(ValueError) as info:
        raise wrangles.function('bad input')
    assert info.typename == 'ValueError' and 'expected message' in info.value.args[0]
```

## Recipe System

### Recipe File Format
Recipes use YAML with `.wrgl.yml`, `.wrgl.yaml` or `.recipe` extensions:

```yaml
read:
  - connector:
      parameter: value

wrangles:
  - wrangle.name:
      input: column_name
      output: result_column

write:
  - connector:
      parameter: value
```

### Running Recipes
```bash
# From terminal
wrangles.recipe recipe.wrgl.yml

# From Python
import wrangles
wrangles.recipe.run('my_recipe.wrgl.yml')

# With custom functions
wrangles.recipe my_other_recipe.recipe -f custom_functions.py
```

### Custom Functions
Custom functions can be added to recipes:
- Define in a separate Python file
- Pass via `functions` parameter or `-f` flag
- Non-hidden methods (not starting with `_`) are automatically discovered

## CI/CD Pipeline

### Branching & Release Flow

Two long-lived branches:

- **`main`** — released, stable. Its container tag is `:latest`.
- **`dev`** — integration branch for work heading to a DEV deployment. Its
  container tag is `:dev`.

Work happens on a short-lived feature branch. Both merge targets are allowed, so
pick the base branch deliberately:

- Base a PR on **`dev`** when the change should be integrated and exercised in
  DEV before it reaches a release.
- Base a PR on **`main`** for a fix that must ship without waiting on whatever
  else is sitting in `dev`. Land it on `dev` too, or it will be reverted the
  next time `dev` merges forward.

`dev` merges into `main` via a PR when its contents are ready to release.

Branch the feature off whichever branch you are targeting. Branching off `main`
and targeting `dev` is allowed but means the branch is missing unreleased `dev`
work, so rebase before merging.

**Pushing to a feature branch runs nothing.** `ci.yml` only listens for pushes to
`main` and `dev`; feature branches are covered by their `pull_request` run, so
open the PR (draft is fine) to get any CI at all.

**Base branch changes the test coverage you get.** The OS/Python matrix is only
widened to Ubuntu + Windows on 3.11 + 3.13 when `main` is the branch or the PR
base. A PR based on `dev` runs Ubuntu / 3.11 only, so cross-platform and 3.13
regressions surface later, at the `dev` → `main` PR. For a change with
platform-specific risk (paths, encodings, native dependencies, subprocesses),
prefer basing on `main`, or verify the other platforms locally.

### Merging never releases anything

Merging to `dev` or `main` publishes a **container image only**. It does not
publish a Python package and does not deploy to any environment.

| Action | Result |
| --- | --- |
| Merge to `dev` | tests, then `:dev` image promoted |
| Merge to `main` | tests, then `:latest` image promoted |
| Manually dispatch `deploy-dev.yml` | `<version>rcN` to CodeArtifact, then DEV deploy in Lambda-Recipes |
| Push a `v*` git tag | `:<version>` image, then CodeArtifact, then PyPI |

Both publishing paths are deliberate human actions, not consequences of a merge:

1. **DEV release** — run `deploy-dev.yml` via workflow dispatch from `dev` or
   `main`, supplying a base version such as `1.20.0`. The `rcN` suffix is
   resolved automatically from the versions already in CodeArtifact. RC builds
   go to CodeArtifact only, never PyPI.
2. **Production release** — bump `version` in `setup.py`, merge to `main`, then
   push a matching `v<version>` tag. `publish-tagged.yml` refuses to run if the
   tag and `setup.py` disagree.

There is no "staging" environment. The environments are DEV (Lambda-Recipes) and
production.

See `.github/RELEASE_RUNBOOK.md` for the full release order and recovery steps.

### GitHub Actions Workflows
- **ci.yml** (*CI*)**:** pushes to `main` / `dev`, and PRs into `main` / `dev`
  - Pytest on Ubuntu + Windows across Python 3.11 + 3.13 when the branch or PR
    base is `main`; Ubuntu / 3.11 only otherwise
  - Test pip installation
  - Generate and test JSON schema
  - Build the Docker image, pushed only on merges to `main` / `dev`
  - Run container tests, then promote the mutable tag
- **deploy-dev.yml** (*Deploy Dev*)**:** manual dispatch from `dev` or `main`.
  RC to CodeArtifact, then DEV deploy in Lambda-Recipes.
- **publish-tagged.yml** (*Deploy Prod*)**:** `v*` tag push. GHCR, then
  CodeArtifact, then PyPI. The file name is pinned by PyPI Trusted Publishing
  and cannot be renamed without updating the publisher on PyPI first.

### Workflow Jobs
1. **pytest:** Run test suite across OS/Python matrix
2. **test-pip-install:** Verify package installs correctly
3. **test-generate-schema:** Generate JSON schema from code
4. **build:** Create Docker image and push to GitHub Container Registry
5. **test-container:** Validate Docker image with full test suite
6. **promote-image:** Retag the tested image as `dev` / `latest`

Mutable tags are only moved after `test-container` passes, and package
publication is gated on the container, so the wheel and the image cannot
diverge. See `.github/RELEASE_RUNBOOK.md` for the release order and for how to
resume a release that fails partway through.

## Known Issues & Workarounds

### TODO Items in Code
Several areas marked for future enhancement:
- **SFTP Testing:** No SFTP server setup for tests yet (`tests/connectors/test_sftp.py`)
- **Database Connectors:** UPDATE and UPSERT not yet implemented for postgres, mssql, mysql
- **Salesforce:** Need better error handling for bulk operation failures
- **Pricefx:** JWT auth not implemented (uses basic auth)
- **Akeneo:** Pagination and error handling need improvement

### macOS Build Dependencies
On macOS, `freetds` must be installed via Homebrew before pip install to support MSSQL connections:
```bash
brew update
brew install freetds
```

### Pandas Performance Warnings
Performance warnings from pandas are suppressed in `recipe.py` as they appear during recipe execution without actual performance impact. This is a known issue being monitored.

### Docker Image Size Optimization
- Botocore data reduced to S3-only (removes ~300MB)
- Pandas test data removed from final image
- Uses slim Debian base image for minimal footprint

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run tests with specific markers
pytest -v tests/test_wrangles.py

# Generate schema
cd schema && python generate_recipe_schema.py

# Build Docker image
docker build -t wrangles:latest .

# Run recipe locally
wrangles.recipe tests/samples/recipe-basic.wrgl.yml

# Install package locally
pip install .
```

## Additional Resources

- **Documentation:** https://wrangles.io/python
- **GitHub Repository:** https://github.com/wrangleworks/WranglesPy
- **Bug Tracker:** https://github.com/wrangleworks/WranglesPy/issues
- **User Registration:** https://sso.wrangle.works (for cloud ML models)
