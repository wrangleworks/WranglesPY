# Wrangles

Full documentation available at [wrangles.io](https://wrangles.io/python).

## Local AI agents and Skills (optional)

`ai.agent` runs inline instructions with optional local Skills.
`ai.skill` applies one named Skill. Both run a headless Copilot SDK session owned
by WranglesPY and use OpenAI inference with your own key. Existing recipes do
not import the SDK or start a runtime.

```sh
pip install 'wrangles[agent]'
python -m copilot download-runtime
```

From a source checkout use `pip install -e '.[agent]'`. This slice pins
`microsoft-copilot-sdk==2.0.3`. The SDK downloads its matching native runtime.
The command above caches it before use. Python 3.11+ and a supported runtime platform are required.
Set `OPENAI_API_KEY` in your process environment, then run the three-row live
acceptance example from this checkout.

```sh
python examples/ai_local/run.py
```

This makes two small billable OpenAI runs. It verifies that Python normalized the
names to `Pump Seal`, `Valve Kit`, `Pump Seal` and counted `2`, `1`, `2` through
the dataframe tools. It prints the resolved Skill and tool names. Set `PYTHONPATH=.`
if you are running the source example without an editable install.

```python
import pandas as pd
import wrangles

df = pd.DataFrame({'Description': ['PUMP seal', 'valve kit', 'pump SEAL'],
                   'Unrelated': [10, 20, 30]})
result = wrangles.recipe.run({'wrangles': [{'ai.agent': {
    'input': ['Description'],
    'output': {'Name': {'type': 'string'}, 'Count': {'type': 'integer'}},
    'instructions': 'Title-case Description into Name. Count rows sharing each Name into Count.',
    'model': 'gpt-5-mini',
    'timeout': 120,
}}]}, dataframe=df)
```

To apply the sample Skill directly, use `ai.skill` with `skill: normalize-products`
and `skill_package: /absolute/path/to/examples/ai_local`. `model_id` also selects
the Skill. With `ai.agent`, supply one `skill` or a list such as
`skills: [{model_id: normalize-products}]`. Both accept a package directory
from `WRANGLES_AGENT_PLUGIN` when the recipe omits `skill_package`.
The inference `model` is independent of the Skill name.
`api_key` can be supplied explicitly, but prefer the environment to keep keys
out of recipe files and ordinary recipe diagnostics.

Local packages have a [1.0 plugin manifest](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json)
declaring the canonical `$schema` and `name`, and a
`skills/<skill-name>/SKILL.md` file. The Skill file requires YAML front matter
with matching `name` and nonblank `description`, followed by its instructions.
Names use lowercase letters/digits separated by hyphens. Copilot's native
Skill provider exposes the selected Skill texts to the session's agent.
This text-only loader restricts resolved files to the configured package.

Use exact `input` column names. The Agent can inspect selected and computed
columns through `read_dataframe`. `convert_case` runs Wrangles `convert.case`
and `count_values` computes frequencies across the selected rows in Python.
Both commit values directly to declared output columns. For semantic grouping,
the Agent can supply group labels by `row_id` to `count_values`. Python binds
those labels to the rows and counts each group. `submit_results` fills any
remaining model-judged columns. A conflicting model value cannot replace a
committed column. When tools fill every column, an empty submission completes
the step. [Live example and observations](examples/ai_local/VALIDATION.md)

Declare each `output` as `string`, `integer`, `number`, or `boolean` with an
optional description. Wrangles validates types, declared fields and the identity
of each submitted row. It restores input order and index, including duplicate
index labels. `row_id` is reserved. Only declared outputs may replace input
columns. A recipe `where` clause limits the dataframe seen by the Agent.

Each call uses a fresh temporary runtime home, disables ambient configuration
and allows only these four dataframe tools. Runtime startup and inference share
the step timeout. Cleanup has a separate bounded deadline. A successful result
stores the selected Skill names and digests, model, tool invocations and
committed column names in `result.attrs['wrangles_ai_runtime']`. This report
describes the latest Agent step. Subsequent pandas operations may discard attrs.

Credential-free acceptance tests are included in the local selection:
`python -m pytest -c pytest-local.ini tests/recipes/wrangles/test_ai_runtime.py`.
These mock the SDK boundary; they do not constitute a live BYOK run. Hosted
deployment, XL integration, persistent bundles, API-Core metadata, and Rai are
outside this increment.

For contributors, the [public AI functions](wrangles/ai/__init__.py) use the
[structured-question implementation](wrangles/ai/_questions.py) and the
[shared cache](wrangles/ai/cache.py). The [Agent runtime](wrangles/ai/agents/runtime.py)
owns Copilot sessions. Add dataframe tools in [tools.py](wrangles/ai/agents/tools.py)
and maintain local Skill loading in [skills.py](wrangles/ai/agents/skills.py).

## Python support

Wrangles supports Python 3.11, 3.12, 3.13, and 3.14. Pull requests targeting
`main` and pushes to `main` run tests and package-install checks on Python 3.11,
3.13, and 3.14 on Ubuntu and Windows. Tagged releases run tests on Python 3.13
and 3.14 on Ubuntu and macOS, plus package-install checks on Ubuntu.

## Local development

The standard local development environment uses Python 3.13. On Windows,
create or refresh the complete test and tooling environment with one command
from the repository root:

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

For regex-based find and replace in recipe columns, use `standardize.replace`:

```yaml
wrangles:
  - standardize.replace:
      input: description
      find: ETA
      replace: Estimated Time of Arrival
```

Omit `output` to update the input column, or set it to write a separate column.
The legacy recipe name `replace` remains supported with the same parameters and
behavior. DataFrame calls support both `df.wrangles.standardize.replace(...)`
and `df.wrangles.replace(...)`.

### Recipes

Recipes are written in YAML and allow a series of Wrangles to be run as an automated sequence.

For targeted web content retrieval with prompts that use values from each row,
see [Retrieve content from links](docs/search_retrieve_link_content.md).

For search-result scoring, filtering, part-code evidence, and output fields, see
[Search-result scoring](docs/search_result_scoring.md).

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

Named workbook table recipes: see [excel.table](docs/excel-tables.md) for the
WranglesXL companion contract, supported actions and integration requirements.
