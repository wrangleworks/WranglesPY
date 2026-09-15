"""Command-line adapters for recipes and saved Extract-AI definitions."""
import argparse as _argparse
import math as _math
import json as _json
import logging as _logging
import re as _re
import sys as _sys
from pathlib import Path as _Path
from . import ai_saved_model as _saved
from . import ai_definition as _definition
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


class _UsageError(Exception):
    pass


class _Parser(_argparse.ArgumentParser):
    """Let the top-level adapter format usage errors consistently."""
    def error(self, message):
        raise _UsageError(message)


def _reject_constant(value):
    raise ValueError('Non-finite JSON numbers are not supported.')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON object keys are not supported.')
        result[key] = value
    return result


def _authoring_error(error, content):
    # Shared validators may include cell values in their exception text. Extract
    # only known locations and fixed guidance, never echo arbitrary content.
    message = str(error)
    location = {'path': '$'}
    match = _re.search(r'(?:on row |row )(\d+)', message)
    if match:
        row = int(match.group(1))
        location.update(row=row, path=f'$.Data[{row - 2}]')
        if isinstance(content, dict) and isinstance(content.get('Columns'), list):
            for index, heading in enumerate(content['Columns']):
                if heading in _saved.KNOWN_HEADINGS and message.startswith(heading):
                    location.update(column=index + 1, heading=heading,
                                    path=f'$.Data[{row - 2}][{index}]')
                    break
    elif 'Settings' in message:
        location['path'] = '$.Settings'
    elif 'Find column' in message:
        location['path'] = '$.Columns'
    guidance = 'Check the value against the saved Extract-AI authoring contract.'
    for marker, explanation in (
        ('Find column is required', 'The Find column is required.'),
        ('Find is required on row', 'Find must be populated on this row.'),
        ('must contain Columns and Data arrays', 'Columns and Data must be arrays.'),
        ('content must be an object', 'The definition must be a JSON object.'),
        ('must be an array with no more values than columns', 'The row must be an array with no more values than columns.'),
        ('must be string, number', 'Type must be string, number, integer, boolean, array, or object.'),
        ('requires Example - Output', 'Example - Input requires Example - Output.'),
        ('must be TRUE or FALSE', 'Use a boolean or TRUE/FALSE text.'),
        ('Settings must be an object', 'Settings must be an object or null.'),
        ("Settings.variant must be 'extract-ai'", "Settings.variant must be 'extract-ai'."),
        ('is required for type object', 'Properties must be populated when supplied for an object.'),
    ):
        if marker in message:
            guidance = explanation
            break
    return {'code': 'authoring_validation', 'message': guidance, **location}


def _runtime_check(content):
    # Runtime compilation is a separate diagnostic. Its logs may contain schema
    # values; suppress those records and return only a safe summary.
    logger = _logging.getLogger(_definition.__name__)
    quiet = _logging.Filter()
    quiet.filter = lambda record: False
    logger.addFilter(quiet)
    try:
        _definition.compile_definition({}, model='validation-only', saved_model_content=content)
        return 'compatible', []
    except (ValueError, TypeError, KeyError, RecursionError) as error:
        location = {}
        match = _re.match(r'Invalid extract.ai definition at model_id\.data\[(\d+)\]', str(error))
        if match:
            index = int(match.group(1)) - 1
            location = {'path': f'$.Data[{index}]', 'row': index + 2}
        return 'incompatible', [{
            **location,
            'code': 'runtime_incompatible',
            'message': 'Authoring validation passed, but the local runtime compiler rejected the definition. Review it before extraction.',
        }]
    finally:
        logger.removeFilter(quiet)


def _validate_file(filename):
    try:
        text = _Path(filename).read_text(encoding='utf-8-sig')
    except (OSError, UnicodeError):
        return 2, {'code': 'input_file', 'message': 'Cannot read the definition as a UTF-8 JSON file.', 'path': '$'}, None
    try:
        content = _json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_unique_object)
    except _json.JSONDecodeError as error:
        return 2, {'code': 'invalid_json', 'message': 'Invalid JSON syntax.',
                   'path': '$', 'line': error.lineno, 'column': error.colno}, None
    except (ValueError, RecursionError):
        return 2, {'code': 'invalid_json', 'message': 'JSON must have unique object keys, finite numbers, and supported nesting.', 'path': '$'}, None
    try:
        prepared = _saved.prepare_content(content)
    except (ValueError, TypeError, RecursionError) as error:
        return 2, _authoring_error(error, content), None
    runtime, warnings = _runtime_check(prepared)
    return 0, None, {'scope': 'saved-model-authoring', 'runtime': runtime,
                     'rows': len(prepared['Data']), 'columns': len(prepared['Columns']),
                     'warnings': warnings}


def _emit_result(command, outcome, error=None, validation=None, json_mode=False):
    result = {'schema_version': 1, 'command': command, 'outcome': outcome,
              'model_id': None, 'readiness': 'not_checked', 'verification': 'not_checked',
              'validation': validation, 'error': error}
    if json_mode:
        # ASCII escapes keep redirected stdout portable on Windows code pages.
        print(_json.dumps(result, ensure_ascii=True, allow_nan=False))
    elif not error:
        print('Valid saved-model definition.')
    if error:
        print(f"{error['code']}: {error['message']}" +
              (f" ({error['path']})" if 'path' in error else '') +
              (f" line {error['line']}, column {error['column']}" if 'line' in error else ''), file=_sys.stderr)
    if validation:
        print('Authoring validation does not guarantee runtime compatibility or extraction quality.', file=_sys.stderr)
        for warning in validation['warnings']:
            print(warning['message'], file=_sys.stderr)


def main(argv=None):
    """Unified command-line entry point."""
    parser = _Parser(
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
    models = commands.add_parser('model', help='Work with saved Extract-AI definitions')
    model_actions = models.add_subparsers(dest='action', required=True)
    validate = model_actions.add_parser(
        'validate', help='Validate a local JSON definition without service calls',
        description='Validate the shared saved-model authoring contract; runtime compatibility and extraction quality are separate.',
        epilog='Example: wrangles model validate "power supply.json" --json')
    validate.add_argument('file', help='UTF-8 JSON document with Columns, Data, and optional Settings')
    validate.add_argument('--json', action='store_true', help='Write one versioned JSON result to stdout')
    arguments = list(_sys.argv[1:] if argv is None else argv)
    json_mode = '--json' in arguments
    command = 'model.validate' if arguments[:2] == ['model', 'validate'] else 'model'
    try:
        args = parser.parse_args(arguments)
    except _UsageError as error:
        if arguments[:1] == ['recipe']:
            _argparse.ArgumentParser.error(parser, str(error))
        _emit_result(command, 'error', {'code': 'usage', 'message': 'Invalid or missing arguments. Run wrangles --help or wrangles model validate --help.'}, json_mode=json_mode)
        raise SystemExit(2)
    if args.command == 'recipe':
        _run_recipe(args)
        return
    try:
        code, error, validation = _validate_file(args.file)
        _emit_result(command, 'invalid' if error else 'valid', error, validation, args.json)
    except KeyboardInterrupt:
        _emit_result(command, 'interrupted', {'code': 'interrupted', 'message': 'Validation interrupted.'}, json_mode=args.json)
        raise SystemExit(130)
    except Exception:
        _emit_result(command, 'error', {'code': 'unexpected', 'message': 'Unexpected local validation failure.'}, json_mode=args.json)
        raise SystemExit(1)
    if code:
        raise SystemExit(code)
