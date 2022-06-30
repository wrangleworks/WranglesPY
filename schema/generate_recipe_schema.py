import wrangles
import json
import yaml

schema = {
    'run': {},
    'read': {},
    'wrangles': {},
    'write': {}
}

# Load base recipe
with open('schema/recipe_base_schema.json', 'r') as f:
  recipe_schema = json.load(f)

# Get all Connector Docs
def getConnectorDocs(schema_wrangles, obj, path):
    """
    Recursively loop through all connector code looking for docs
    """
    non_hidden_methods = [conn for conn in dir(obj) if not conn.startswith('_')]

    if len(non_hidden_methods) > 0:
        for method in non_hidden_methods:
            getConnectorDocs(schema_wrangles, getattr(obj, method), '.'.join([path, method]))

    if '_schema' in dir(obj):
        if 'read' in obj._schema.keys():
            schema['read'][path[1:]] = yaml.safe_load(obj._schema['read'])

        if 'write' in obj._schema.keys():
            schema['write'][path[1:]] = yaml.safe_load(obj._schema['write'])

        if 'run' in obj._schema.keys():
            schema['run'][path[1:]] = yaml.safe_load(obj._schema['run'])

getConnectorDocs(schema, wrangles.connectors, '')

# Add special read functions - join, union, concatenate
join = """
type: object
description: Join two data sources on key(s). Equivalent to a join in SQL.
required:
  - how
  - left_on
  - right_on
  - sources
properties:
  how:
    type: string
    description: Method of join
    enum:
      - left
      - right
      - outer
      - inner
      - cross
  left_on:
    type:
      - string
      - array
    description: Key(s) to join on from first source
  right_on:
    type:
      - string
      - array
    description: Key(s) to join on from second source
  sources:
    type: array
    description: Two data sources to be joined
    minItems: 2
    maxItems: 2
    items:
      "$ref": "#/$defs/sources/read"
"""
schema['read']['join'] = yaml.safe_load(join)

union = """
type: object
description: Combine two or more data sets together, stacked vertically. Equivalent to a union in SQL.
required:
  - sources
properties:
  sources:
    type: array
    description: Two data sources to be combined
    minItems: 2
    items:
      "$ref": "#/$defs/sources/read"
"""
schema['read']['union'] = yaml.safe_load(union)

concatenate = """
type: object
description: Combine two or more data sets together, stacked horizontally.
required:
  - sources
properties:
  sources:
    type: array
    description: Two data sources to be combined
    minItems: 2
    items:
      "$ref": "#/$defs/sources/read"
"""
schema['read']['concatenate'] = yaml.safe_load(concatenate)


# Add special write function for dataframe
write_dataframe = """
type: object
description: Define the dataframe that is returned from the recipe.run() function
required:
  - columns
properties:
  columns:
    type: array
    description: List of columns to include in the returned dataframe
  excluded_columns:
    type: array
    description: List of columns to exclude from the returned dataframe
"""
schema['write']['dataframe'] = yaml.safe_load(write_dataframe)


# Get all Wrangle element docs
def getMethodDocs(schema_wrangles, obj, path):
    """
    Recursively loop through all non-hidden function and
    look for appropriately formatted docstrings
    """
    non_hidden_methods = [conn for conn in dir(obj) if not conn.startswith('_')]

    if len(non_hidden_methods) > 0:
        for method in non_hidden_methods:
            if method != 'main':
                getMethodDocs(schema_wrangles, getattr(obj, method), '.'.join([path, method]))
    else:
        try:
            schema_wrangle = yaml.safe_load(obj.__doc__)
            if 'type' in schema_wrangle.keys():
                schema_wrangles[path[1:]] = schema_wrangle
        except:
            pass

getMethodDocs(schema['wrangles'], wrangles.recipe._recipe_wrangles, '')


# Construct final schema
recipe_schema['$defs']['sources']['read']['properties'] = schema['read']
recipe_schema['properties']['write']['items']['properties'] = schema['write']
recipe_schema['$defs']['actions']['properties'] = schema['run']
recipe_schema['properties']['wrangles']['items']['properties'] = schema['wrangles']


# Write final schema
with open('schema_dev.json', 'w') as f:
    json.dump(recipe_schema, f)