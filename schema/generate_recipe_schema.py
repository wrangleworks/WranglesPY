import wrangles
import json
import yaml

schema = {
    'read': {},
    'wrangles': {},
    'write': {}
}

# Load base recipe
with open('recipe_base_schema.json', 'r') as f:
  recipe_schema = json.load(f)

# Get all connector schema
connectors = [conn for conn in dir(wrangles.connectors) if not conn.startswith('_')]
for name in connectors:
    connector = getattr(wrangles.connectors, name)
    if '_schema' in dir(connector):
        if 'read' in connector._schema.keys():
            schema['read'][name] = yaml.safe_load(connector._schema['read'])

        if 'write' in connector._schema.keys():
            schema['write'][name] = yaml.safe_load(connector._schema['write'])

join = """
type: object
description: Join two data sources on key(s). Analogous to a join in SQL.
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

concatenate = """
type: object
description: Concatenate two data sets together. Analogous to a union in SQL.
required:
  - sources
properties:
  sources:
    type: array
    description: Two data sources to be joined
    minItems: 2
    items:
      "$ref": "#/$defs/sources/read"
  axis:
    type: integer
    description: 0 to stack vertically (default). 1 to stack horizontally.
"""
schema['read']['concatenate'] = yaml.safe_load(concatenate)


recipe_schema['$defs']['sources']['read']['properties'] = schema['read']
recipe_schema['properties']['write']['items']['properties'] = schema['write']




pipeline_wrangles = [conn for conn in dir(wrangles.pipeline._pipeline_wrangles) if not conn.startswith('_')]
for name in pipeline_wrangles:
    pipeline_wrangle = getattr(wrangles.pipeline._pipeline_wrangles, name)
    if '_schema' in dir(pipeline_wrangle):
        for key, val in pipeline_wrangle._schema.items():
            if name == 'main':
                schema['wrangles'][key] = yaml.safe_load(val)
            else:
                schema['wrangles'][f'{name}.{key}'] = yaml.safe_load(val)


recipe_schema['properties']['wrangles']['items']['properties'] = schema['wrangles']


# Write final schema
with open('recipes_schema.json', 'w') as f:
    json.dump(recipe_schema, f)