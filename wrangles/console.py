"""
Wrangles Package Console Functions
"""
import argparse as _argparse
from types import ModuleType as _ModuleType
from inspect import isfunction as _isfunction
from . import recipe as _recipe


def recipe():
    """
    Enable console execution of a Wrangles recipe

    >>> wrangles.recipe recipe.wrgl.yml --functions custom_functions.py --variables custom_variables.py
    """
    # Define console function
    parser = _argparse.ArgumentParser(prog ='wrangles.recipe', description ='Run a Wrangles Recipe')
  
    parser.add_argument('recipe', type = open, help = 'The filename of the recipe')
    parser.add_argument('--functions', type=open, help ='A file of custom functions')
    parser.add_argument('--variables', type=open, help ='A file containing custom variables')
    parser.add_argument('--varDict', type=str, help ='The name of the dictionary within the custom variables file. Default variables.')

    args = parser.parse_args()


    # If the user has specified a file of custom variables, import those
    if args.variables is not None:
        custom_variables = _ModuleType('custom_variables')
        exec(args.variables.read(), custom_variables.__dict__)
        variables = getattr(custom_variables, args.varDict or 'variables')
    else:
        variables = {}

    # Run the recipe
    _recipe.run(args.recipe.read(), variables=variables)
