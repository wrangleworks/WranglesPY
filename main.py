import wrangles
import os
import importlib.util
import sys


# If the user has provided a file of custom functions, add those
functions = []
if os.environ.get("WRANGLES_CUSTOM_FUNCTIONS"):
    file_path = os.environ.get("WRANGLES_CUSTOM_FUNCTIONS")
    spec = importlib.util.spec_from_file_location('custom_functions', file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules['custom_functions'] = module
    spec.loader.exec_module(module)

    functions = [getattr(module, method) for method in dir(module) if not method.startswith('_')]


wrangles.recipe.run(os.environ["WRANGLES_RECIPE"], functions=functions)