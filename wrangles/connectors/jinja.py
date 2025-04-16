"""
Use JINJA to manipulate a template
"""
from ..utils import optional_import as _optional_import

# Store lazy imports
_lazy_imports = {}


_schema = {}


def run(template: dict, context: dict, output_file: str):
    """
    Create a jinja template
    :param template: A generic template used to generate a more specific template to be used
    :param context: A dictionary used to define the output template
    :param output_file: File name/path for the file to be output
    """
    # Lazy import external dependencies
    if not _lazy_imports.get('jinja2'):
        _lazy_imports['jinja2'] = _optional_import('jinja2')

    if 'file' in template:
        template = _lazy_imports['jinja2'].Environment(
            loader=_lazy_imports['jinja2'].FileSystemLoader(''),
            trim_blocks=True,
            lstrip_blocks=True
        ).get_template(template['file'])

    elif 'string' in template:
       template = _lazy_imports['jinja2'].Environment(loader=_lazy_imports['jinja2'].BaseLoader).from_string(template['string'])

    else:
       raise ValueError('jinja: Either a file or string must be provided for the template')
    
    # writing the file makes it easy to see what the Description template does
    with open (output_file, 'w') as f:
        f.write(template.render(context))

_schema['run'] = """
type: object
description: Use a Jinja template with a context to create a file
additionalProperties: false
required:
  - template
  - context
  - output_file
properties:
  template:
    type: object
    additionalProperties: false
    description: The template to apply the values to. Either a file or string.
    properties:
      file:
        type: string
        description: A .jinja file containing the template
      string:
        type: string
        description: A string which is used as the jinja template
  context:
    type: object
    description: A dictionary used to define the output template
  output_file:
    type: string
    description: File name/path for the file to be output
"""
