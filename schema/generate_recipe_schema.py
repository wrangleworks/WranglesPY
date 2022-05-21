import wrangles
import json
import yaml

schema = {
    'read': [],
    'wrangles': [],
    'write': []
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
            schema_temp = {
                'type': 'object',
                'properties': {
                    name: yaml.safe_load(connector._schema['read'])
                }
            }
            schema['read'].append(schema_temp)

        if 'write' in connector._schema.keys():
            schema_temp = {
                'type': 'object',
                'properties': {
                    name: yaml.safe_load(connector._schema['write'])
                }
            }
            schema['write'].append(schema_temp)

recipe_schema['properties']['read']['oneOf'] = schema['read']
recipe_schema['properties']['write']['items']['anyOf'] = schema['write']




pipeline_wrangles = [conn for conn in dir(wrangles.pipeline._pipeline_wrangles) if not conn.startswith('_')]
for name in pipeline_wrangles:
    pipeline_wrangle = getattr(wrangles.pipeline._pipeline_wrangles, name)
    if '_schema' in dir(pipeline_wrangle):
        for key, val in pipeline_wrangle._schema.items():
            if name == 'main':
                schema_temp = {
                    'type': 'object',
                    'properties': {
                        f'{key}': yaml.safe_load(val)
                    }
                }
                schema['wrangles'].append(schema_temp)
            else:
                schema_temp = {
                    'type': 'object',
                    'properties': {
                        f'{name}.{key}': yaml.safe_load(val)
                    }
                }
                schema['wrangles'].append(schema_temp)


recipe_schema['properties']['wrangles']['items']['anyOf'] = schema['wrangles']


# Write final schema
with open('recipe_schema.json', 'w') as f:
    json.dump(recipe_schema, f)