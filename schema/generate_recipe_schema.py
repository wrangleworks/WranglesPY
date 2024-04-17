import sys
import os
import json
import logging
import yaml
import requests
import jsonschema

# Get the parent directory of the current file
# and add it to the path so we can import the wrangles module
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
import wrangles

schema = {
    'run': {},
    'read': {},
    'wrangles': {},
    'write': {}
}

# Load base recipe
with open('recipe_base_schema.json', 'r') as f:
  recipe_schema = json.load(f)

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

# Add special read functions
schema['read']['join'] = yaml.safe_load(
    """
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
          "$ref": "#/$defs/read/items"
    """
)
schema['read']['union'] = yaml.safe_load(
    """
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
          "$ref": "#/$defs/read/items"
    """
)
schema['read']['concatenate'] = yaml.safe_load(
    """
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
          "$ref": "#/$defs/read/items"
    """
)

# Add special write functions
schema['write']['dataframe'] = yaml.safe_load(
    """
    type: object
    description: Define the dataframe that is returned from the recipe.run() function
    properties: {}
    """
)


def getMethodDocs(schema_wrangles, obj, path):
    """
    Recursively loop through all non-hidden function and
    look for appropriately formatted docstrings
    """
    non_hidden_methods = [conn for conn in dir(obj) if not conn.startswith('_')]

    if len(non_hidden_methods) > 0:
        for method in non_hidden_methods:
            # Prevent including methods twice that are referenced at the root
            if method not in ('main', 'pandas'):
                getMethodDocs(schema_wrangles, getattr(obj, method), '.'.join([path, method]))
    else:
        try:
            schema_wrangle = yaml.safe_load(obj.__doc__)
            if 'type' in schema_wrangle.keys() or 'anyOf' in schema_wrangle.keys():
                schema_wrangles[path[1:]] = schema_wrangle
        except Exception as e:
            logging.warning(f'{obj} description={e}')

getMethodDocs(schema['wrangles'], wrangles.recipe._recipe_wrangles, '')


# Add common wrangle properties
for wrangle in schema['wrangles']:
    if "properties" not in schema['wrangles'][wrangle]:
        schema['wrangles'][wrangle]["properties"] = {}

    if wrangle not in wrangles.config.no_where_list:
        schema['wrangles'][wrangle]['properties']['where'] = {
            "$ref": "#/$defs/wrangles/commonProperties/where"
        }
    else:
        schema['wrangles'][wrangle]['properties']['where'] = {
            "$ref": "#/$defs/wrangles/commonProperties/where_special"
        }
    schema['wrangles'][wrangle]['properties']['where_params'] = {
        "$ref": "#/$defs/wrangles/commonProperties/where_params"
    }

# Add common write properties
for write in schema['write']:
    if "properties" in schema['write'][write]:
        write_properties = schema['write'][write]['properties']
    else:
        write_properties = schema['write'][write]['anyOf'][-1]['properties']

    for x in ["columns", "not_columns", "where", "where_params", "order_by"]:
        write_properties[x] = {
            "$ref": f"#/$defs/write/commonProperties/{x}"
        }

# Add common read properties
for read in schema['read']:
    if "properties" in schema['read'][read]:
        read_properties = schema['read'][read]['properties']
    else:
        read_properties = schema['read'][read]['anyOf'][-1]['properties']

    for x in ["columns", "not_columns", "where", "where_params", "order_by"]:
        read_properties[x] = {
            "$ref": f"#/$defs/write/commonProperties/{x}"
        }

# Construct final schema
recipe_schema['$defs']['read']['items']['properties'] = schema['read']
recipe_schema['$defs']['write']['items']['properties'] = schema['write']
recipe_schema['$defs']['run']['items']['properties'] = schema['run']
recipe_schema['$defs']['wrangles']['items']['properties'] = schema['wrangles']

# Validate the generated schema
jsonschema.validate(recipe_schema, requests.get('http://json-schema.org/draft-07/schema#').json())

# Write final schema
with open('schema.json', 'w') as f:
    json.dump(recipe_schema, f)
