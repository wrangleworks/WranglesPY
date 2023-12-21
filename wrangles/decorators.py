"""
Reusable decorators for use around the application.
"""
import functools as _functools
import inspect as _inspect


def format_input_output(require_consistent_length=False):
    """
    Decorator to ensure input and output are lists for recipe wrangles.
    If not, the item will be added to a list of length 1.
    If output is none, output is set to input.

    :param require_consistent_length: If True, will raise an error if \
        input and output are not equal lengths
    """
    def decorator_wrapper(func):
        @_functools.wraps(func)
        def validate_input_output_columns(*args, **kwargs):
            # Get args regardless of named or positional
            bound_func = _inspect.signature(func).bind(*args, **kwargs)
            arguments = bound_func.arguments
            # If output is not specified, overwrite input columns in place
            if arguments.get("output") is None:
                arguments["output"] = arguments["input"]

            # If a string provided, convert to lists
            if not isinstance(arguments["input"], list):
                arguments["input"] = [arguments["input"]]
            if not isinstance(arguments["output"], list):
                arguments["output"] = [arguments["output"]]

            # If specified, ensure input and output are equal lengths
            if (
                require_consistent_length
                and len(arguments["input"]) != len(arguments["output"])
                and len(arguments["output"]) > 1
            ):
                raise ValueError("The lists for input and output must be the same length.")
            
            return func(*bound_func.args, **bound_func.kwargs)

        return validate_input_output_columns
    return decorator_wrapper


def first_element_option(default=""):
    """
    Allow a first_element argument.
    If used, will return the first element of the list.

    This assumes an output of the form
    >>> [value1, value2, ...] => value1
    or
    >>> {key1: [value1, value2, ...], ...]} => {key1: value1, ...}

    :param default: The default value to return if the list is empty
    """
    def decorator_wrapper(func):
        @_functools.wraps(func)
        def validate_input_output_columns(*args, **kwargs):
            # Get args regardless of named or positional
            bound_func = _inspect.signature(func).bind(*args, **kwargs)
            arguments = bound_func.arguments
            df = func(*bound_func.args, **bound_func.kwargs)

            # If user has specified first_element, return the first element
            if arguments.get("first_element", False):
                def get_first_element(value):
                    if isinstance(value, list):
                        return value[0] if len(value) >= 1 else default
                    elif isinstance(value, dict):
                        return {
                            k: get_first_element(v)
                            for k, v in value.items()
                        }
                    else:
                        return value

                for column in arguments.get("output", []):
                    df[column] = [
                        get_first_element(x)
                        for x in df[column]
                    ]

            return df
        return validate_input_output_columns
    return decorator_wrapper
