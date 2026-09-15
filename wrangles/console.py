"""Command-line entry points for local Wrangles recipes."""
import argparse as _argparse
import math as _math
from importlib.metadata import version as _version
from types import ModuleType as _ModuleType
from . import recipe as _recipe


def _timeout(value):
    try:
        seconds = float(value)
    except ValueError as exc:
        raise _argparse.ArgumentTypeError('timeout must be a non-negative number of seconds') from exc
    if not _math.isfinite(seconds) or seconds < 0:
        raise _argparse.ArgumentTypeError('timeout must be a finite, non-negative number of seconds')
    return seconds


def _recipe_arguments(parser):
    parser.add_argument('recipe', help='Recipe file, URL, saved model ID, or inline recipe')
    parser.add_argument('--functions', '-f', help='Python file containing custom functions')
    parser.add_argument('--variables', '-v', help='Python file to execute for custom variables')
    parser.add_argument('--varDict', help='Dictionary in the variables file (default: variables)')
    parser.add_argument('--timeout', '-t', type=_timeout,
                        help='Recipe timeout in seconds (default: unlimited)')


def _run_recipe(args):
    variables = {}
    if args.variables is not None:
        custom_variables = _ModuleType('custom_variables')
        with open(args.variables) as source:
            exec(source.read(), custom_variables.__dict__)
        variables = getattr(custom_variables, args.varDict or 'variables')
    # Recipe destinations are defined by the recipe. Do not return its dataframe
    # to console_scripts, which would interpret it as an unsuccessful exit code.
    _recipe.run(args.recipe, functions=args.functions, variables=variables,
                timeout=args.timeout)


def recipe(argv=None):
    """Compatible entry point for ``wrangles.recipe RECIPE``."""
    parser = _argparse.ArgumentParser(prog='wrangles.recipe', description='Run a Wrangles recipe')
    _recipe_arguments(parser)
    _run_recipe(parser.parse_args(argv))


def main(argv=None):
    """Unified command-line entry point."""
    parser = _argparse.ArgumentParser(
        prog='wrangles', description='Run Wrangles workflows from the terminal',
        epilog='Example: wrangles recipe run example.wrgl.yml --timeout 60')
    parser.add_argument('--version', action='version', version=f'wrangles {_version("wrangles")}')
    commands = parser.add_subparsers(dest='command', required=True)
    recipes = commands.add_parser('recipe', help='Run a local recipe', description='Local recipe execution')
    actions = recipes.add_subparsers(dest='action', required=True)
    run = actions.add_parser('run', help='Execute a recipe',
                            description='Execute a recipe; output destinations are defined in the recipe.',
                            epilog='Example: wrangles recipe run example.wrgl.yml -f functions.py -v variables.py')
    _recipe_arguments(run)
    _run_recipe(parser.parse_args(argv))
