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

- **Python:** 3.10, 3.11, 3.12, 3.13 (multi-version support)
- **Core Dependencies:** pandas (>=2.0), numpy, polars (1.33.0), pyyaml
- **Database Connectors:** sqlalchemy, pymssql, psycopg2-binary, pymysql, pymongo
- **Cloud/External:** boto3 (AWS S3), simple-salesforce, fabric (SFTP)
- **Data Formats:** openpyxl (Excel), xlsxwriter
- **AI/ML:** OpenAI integration, Hugging Face models
- **Testing:** pytest (8.4.2), pytest-mock, lorem (test data generation)
- **Containerization:** Docker (Python 3.10.16-slim-bookworm base)

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

### Standard Installation
```bash
pip install --upgrade pip
pip install pytest==7.4.4 lorem pytest-mock
pip install -r requirements.txt
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
- Base image: `mcr.microsoft.com/devcontainers/python:1-3.12-bullseye`
- Auto-installs pytest, lorem, pytest-mock on creation
- Includes YAML schema validation for `.wrgl.yml` files
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
Recipes use YAML with `.wrgl.yml` or `.wrgl.yaml` extensions:

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
wrangles.recipe.run('recipe.wrgl.yml')

# With custom functions
wrangles.recipe recipe.wrgl.yml -f custom_functions.py
```

### Custom Functions
Custom functions can be added to recipes:
- Define in a separate Python file
- Pass via `functions` parameter or `-f` flag
- Non-hidden methods (not starting with `_`) are automatically discovered

## CI/CD Pipeline

### GitHub Actions Workflows
- **publish-main.yml:** Main CI pipeline
  - Pytest on multiple OS (Ubuntu, Windows, macOS-14, macOS-latest)
  - Tests Python 3.10, 3.11, 3.12, 3.13
  - Test pip installation
  - Generate and test JSON schema
  - Build and push Docker image
  - Run container tests

### Workflow Jobs
1. **pytest:** Run test suite across OS/Python matrix
2. **test-pip-install:** Verify package installs correctly
3. **test-generate-schema:** Generate JSON schema from code
4. **build:** Create Docker image and push to GitHub Container Registry
5. **test-container:** Validate Docker image with full test suite

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
