# Wrangles

Full documentation available at [wrangles.io](https://wrangles.io/python).

Documentation for the unreleased `search.ai_mode` wrangle is available in
[docs/search-ai-mode.md](docs/search-ai-mode.md).

## Local development

Supported local development uses Python 3.13. On Windows, create or refresh the
complete test and tooling environment with one command from the repository
root:

```powershell
.\scripts\bootstrap-dev.ps1
```

Add `-RunTests` to run the self-contained local test suite after installation. The script
creates `.venv`, installs `requirements-dev.txt` and this checkout in editable
mode, runs `pip check`, and verifies representative core and SQL connector
imports. It will not replace an existing environment created with another
Python version.

If `.venv` was created with an older Python version and can be discarded,
deactivate it and recreate it from the committed declaration:

```powershell
deactivate
Remove-Item -LiteralPath .\.venv -Recurse -Force
.\scripts\bootstrap-dev.ps1 -RunTests
.\.venv\Scripts\Activate.ps1
```

Dev Containers and Codespaces use the same Python 3.13 developer declaration
automatically. `pytest-local.ini` is the shared credential-safe test selection.
`scripts/test-local.ps1` clears credential variables before running it and
isolates generated pytest state by Windows identity. The configuration excludes
the intentionally live database, AWS, WrangleWorks, AI, and search-provider
checks. The complete credentialed suite remains a CI validation and a local
dependency/import pass does not claim live-service validation.

## Container and deployment ownership

The repository-root `dockerfile` builds the WranglesPY **CI test image** published
to `ghcr.io/wrangleworks/wrangles`. It validates the installable package and
recipe behavior in a slim Linux environment; it is not the deployed recipe
runtime.

The production `execute-recipe` AWS Lambda image is built, published to ECR, and
deployed from the
[`wrangleworks/Lambda-Recipes`](https://github.com/wrangleworks/Lambda-Recipes)
repository. Its `dockerfile` is the source of truth for the production Python
version. Changing the Python version in this repository's test image does not
migrate the production Lambda runtime.

## What are Wrangles?

Wrangles are a set of modular transformations for data cleaning and enrichment. Each Wrangle is optimized for a particular job, many of which are backed by sophisticated machine learning models.

With Wrangles, you can:
- Extract information from a set of messy descriptions.
- Predict which category items belong to.
- Standardize text data to a desired format.
- Move data from one system to another.
- Much more...

Wrangles are system independent, and allow you to pull data from one system, transform it and push it to another. Wrangles can be incorporated directly into python code, or an automated sequence of wrangles can be run as a recipe.

## Installation

The python package can be installed using [pip](https://pip.pypa.io/en/stable/getting-started/).

```shell
pip install wrangles
```

This installs the core package, which covers the vast majority of use cases: all data wrangles, recipe execution, Excel/CSV/JSON file I/O, HTTP connectors, SQLite, DuckDB, MongoDB, AWS S3, Salesforce, SFTP/SSH, notifications, and the OpenAI/Gemini/SerpAPI integrations.

### Full install (adds SQL Server, Access, PostgreSQL, MySQL, and Parquet files)

A handful of connectors depend on heavier, more platform-specific packages (SQL database drivers) and aren't included by default:

| Capability | Package(s) |
|---|---|
| Microsoft SQL Server | `pymssql`, `sqlalchemy` |
| Microsoft Access | `pyodbc` |
| PostgreSQL | `psycopg2-binary`, `sqlalchemy` |
| MySQL | `sqlalchemy` (`pymysql` itself is already in the core install) |
| Parquet files | `pyarrow` |

Install just the ones you need (e.g. `pip install pyodbc` for Access only), or install all of them at once:

```shell
pip install sqlalchemy pyodbc pymssql psycopg2-binary pyarrow
```

If you're working from a clone of this repository (e.g. for local development), `pip install -r requirements-full.txt` does the same thing, plus everything from the core install.

> If a connector is used without its required package installed, Wrangles will raise a clear `ImportError` with the exact `pip install` command needed, so there's no harm in starting with the core install and adding packages only as you need them.

Once installed, import the package into your code.
```python
import wrangles
```

## Authentication
Some Wrangles use cloud based machine learning models. To use them a WrangleWorks account is required.

> Create a WrangleWorks account: [Register](https://sso.wrangle.works/auth/realms/wrwx/protocol/openid-connect/registrations?client_id=account&response_type=code&scope=openid%20email&redirect_uri=https://sso.wrangle.works/auth/realms/wrwx/account/#/)

There are two ways to provide the credentials:

### Environment Variables
The credentials can be saved as the environment variables:

- `WRANGLES_USER`
- `WRANGLES_PASSWORD`

### Method
The credentials can be provided within the python code using the authenticate method, prior to calling other functions.
```python
wrangles.authenticate('<user>', '<password>')
```

## Usage

### Functions

Wrangles can be used as functions, directly incorporated into python code.

Wrangles broadly accept a single input string, or a list of strings. If a list is provided, the results will be returned in an equivalent list in the same order and length as the original.

```python
# Extract alphanumeric codes from a free text strings - e.g. find all part numbers in a set of product description
>>> import wrangles

>>> wrangles.extract.codes('replacement part ABCD1234ZZ')
['ABCD1234ZZ']

>>> wrangles.extract.codes(['replacement part ABCD1234ZZ', 'NNN555BBB this one has two XYZ789'])
[
    ['ABCD1234ZZ'],
    ['NNN555BBB', 'XYZ789']
]
```

#### Integrated text cleaning

`standardize.clean` repairs common mojibake, HTML character references,
Unicode inconsistencies, control characters, and whitespace locally. It accepts
a string or list and preserves that shape:

```python
>>> wrangles.standardize.clean(["FranÃ§ais", " AT&amp;T "])
['Français', 'AT&T']
```

In a recipe, one input maps to one output and an omitted output overwrites the
input. Multiple inputs map positionally to equally many outputs, or concatenate
row values when a single output is given. Wildcard-expanded inputs follow the
same rules.

```yaml
wrangles:
  - standardize.clean:
      input: Description *
      output: Clean Description
      separator: " | "
      normalization: NFKC
      preserve_line_breaks: true
```

Common options include `fix_encoding`, `unescape_html`, `normalization`,
`fix_character_width`, `uncurl_quotes`, `remove_control_chars`,
`collapse_whitespace`, `preserve_line_breaks`, and `trim`. Less-common
`ftfy.fix_text` options are forwarded by name. This wrangle does not detect raw
byte encodings or remove HTML tags.

The existing model-backed `standardize` name remains supported and is also
available explicitly as `standardize.custom`.

### Recipes

Recipes are written in YAML and allow a series of Wrangles to be run as an automated sequence.

Recipes can be triggered either from python code or a terminal command.
#### Run
```python
# PYTHON
import wrangles
wrangles.recipe.run('recipe.wrgl.yml')
```
```bash
# TERMINAL
wrangles.recipe recipe.wrgl.yml
```

#### Recipe
```yaml
# file: recipe.wrgl.yml
# ---
# Convert a CSV file to an Excel file
# and change the case of a column.
read:
  - file:
      name: file.csv

wrangles:
  - convert.case:
      input: my column
      case: upper

write:
  - file:
      name: file.xlsx
```
