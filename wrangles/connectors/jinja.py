"""
Use JINJA to manipulate a template
"""
from jinja2 import Environment as _Environment, FileSystemLoader as _FileSystemLoader


_schema = {}


def run(template, context_dictionary, output_file):
    """
    Create a jinja template
    :param template: A generic template used to generate a more specific template to be used
    :param context_dictionary: A dictionary used to define the output template
    :param output_file: File name/path for the file to be output
    """
    env = _Environment(loader=_FileSystemLoader(''),trim_blocks=True, lstrip_blocks=True)
    template = env.get_template(template)
    # writing the file makes it easy to see what the Description template does
    with open (output_file, 'w') as f:
        f.write(template.render(context_dictionary))

_schema['run'] = """
type: object
description: Create a jinja template
required:
  - template
  - context_dictionary
  - output_file
properties:
  template:
    type: string
    description: A generic template used to generate a more specific template to be used
  context_dictionary:
    type: object
    description: A dictionary used to define the output template
  output_file:
    type: string
    description: File name/path for the file to be output
"""
