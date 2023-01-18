# Wrangles

Full documentation available at [wrangles.io](https://wrangles.io/python).

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
