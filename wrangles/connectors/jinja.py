"""
Use JINJA to manipulate a template
"""
from jinja2 import Environment as _Environment, FileSystemLoader as _FileSystemLoader


_schema = {}


def run(gen_template, template_defn, output_file):
    """
    Create a jinja template
    :param gen_tamplate: A generic template used to generate a more specific template to be used
    :param template_defn: A dictionary used to define the output template
    :param output_file: File name/path for the file to be output
    """
    env = _Environment(loader=_FileSystemLoader('templates/'),trim_blocks=True, lstrip_blocks=True)
    gen_template = env.get_template(gen_template)
    # writing the file makes it easy to see what the Description template does
    with open (output_file, 'w') as f:
        f.write(gen_template.render(template_defn))

_schema['run'] = """
type: object
description: Create a jinja template
required:
  - gen_template
  - template_defn
  - output_file
properties:
  gen_template:
    type: string
    description: A generic template used to generate a more specific template to be used
  template_defn:
    type: object
    description: A dictionary used to define the output template
  output_file:
    type: string
    description: File name/path for the file to be output
"""
