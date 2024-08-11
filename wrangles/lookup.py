from typing import Union as _Union
from . import config as _config
from . import data as _data
from . import batching as _batching
import json as _json

def lookup(
    input: _Union[str, list],
    model_id: str,
    columns: _Union[str, list] = None,
    **kwargs
) -> _Union[str, list]:
    """
    Find information using a lookup wrangle. Requires WrangleWorks Account.
    
    :param input: A value or list of values to be looked up.
    :param model_id: The model to be used.
    :param columns: (Optional) The columns to be returned. If not provided, all columns will be returned as a dict.
    """
    # Check if user has entered a single input or multiple inputs
    single_input = False
    if not isinstance(input, list):
        input = [input]
        single_input = True

    # Check if user has entered a single column, multiple columns or not specified
    single_columns = False
    if not isinstance(columns, list) and columns is not None:
        columns = [columns]
        single_columns = True

    # If the Model Id is not appropriate, raise error (Only for Recipes)
    if isinstance(model_id, dict):
        raise ValueError('Incorrect model_id type.\nIf using Recipe, may be missing "${ }" around value')

    # Checking to see if GUID format is correct
    if [len(x) for x in model_id.split('-')] != [8, 4, 4]:
        raise ValueError('Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX')

    metadata = _data.model(model_id)
    # If model_id format is correct but no mode_id exists
    if metadata.get('message', None) == 'error':
        raise ValueError('Incorrect model_id.\nmodel_id may be wrong or does not exists')

    # Set default batch size
    if metadata.get("variant", "key") == "embedding":
        batch_size = 20
    else:
        batch_size = 1000
    batch_size = metadata.get('batch_size') or batch_size
    
    # Using model_id in wrong function
    purpose = metadata['purpose']
    if purpose != 'lookup':
        raise ValueError(
            f'Using {purpose} model_id {model_id} in a lookup wrangle.'
        )

    results = _batching.batch_api_calls(
        f'{_config.api_host}/wrangles/lookup',
        {
            "model_id": model_id,
            "columns": _json.dumps(columns or metadata["settings"]["columns"]),
            **kwargs
        },
        input,
        batch_size
    )

    if columns is None:
        # If no columns specified, return as [{"col1": "val1", ...}, ...]
        results = [
            {col: val for col, val in zip(results["columns"], row)}
            for row in results["data"]
        ]
    elif single_columns:
        # If single column specified, return as 1D array [val1, ...]
        results = [r[0] for r in results["data"]]
    else:
        # If multiple columns specified, return as 2D array [[val1, ...], ...]
        results = results["data"]

    # If input was a single value, return a single value
    if single_input:
        results = results[0]

    return results
