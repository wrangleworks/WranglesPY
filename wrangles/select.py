"""
Select subsets of input data
"""
from typing import Union as _Union
import json as _json
import itertools as _itertools
from .utils import wildcard_expansion_dict

def highest_confidence(data_list):
    """
    Select the option with the highest confidence from multiple columns
    """
    results = []
    for row in data_list:
        highest_confidence = 0
        highest_result = None
        for cell in row:
            if isinstance(cell, str): cell = cell.split(' || ')
            if float(cell[1]) > highest_confidence:
                highest_result = cell
                highest_confidence = float(cell[1])

        results.append(highest_result)
        
    return results


def confidence_threshold(list_1, list_2, threshold):
    """
    Select the first option if it exceeds a given threshold, else the second option.
    """
    results = []
    
    for cell_1, cell_2 in zip(list_1, list_2):
        if isinstance(cell_1, str): cell_1 = cell_1.split(' || ')
        
        if cell_1 == None:
            if isinstance(cell_2, list):
                results.append(cell_2[0])
            else:
                results.append(cell_2)
        elif float(cell_1[1]) > threshold:
            results.append(cell_1[0])
        else:
            if isinstance(cell_2, list):
                results.append(cell_2[0])
            else:
                results.append(cell_2)
            
    return results


def list_element(input, n: _Union[str, int], default = ""):
    """
    Select a numbered element of a list (zero indexed).
    """
    def _int_or_none(val):
        try:
            return int(val)
        except:
            if val:
                raise ValueError(f"{val} is not a valid index to slice on")
            else:
                return None

    def _list_get(lst, index, default=None):
        if isinstance(lst, str) and lst.startswith("["):
            lst = _json.loads(lst)
            
        try:
            return lst[index]
        except IndexError:
            return default

    if ":" in str(n):
        slicer = slice(*map(_int_or_none, str(n).split(":")))
    else:
        slicer = int(n)
        
    return [
        _list_get(row, slicer, default)
        for row in input
    ]


def dict_element(input: _Union[list, dict], key: _Union[str, list], default: any=""):
    """
    Select an element or elements of a dictionary
    """
    # Ensure input is a list
    single_input = False
    if not isinstance(input, list):
        input = [input]
        single_input = True
    
    if isinstance(key, list):
        key = dict(
            _itertools.chain.from_iterable(
                [
                    x.items() if isinstance(x, dict)
                    else {x: x}.items()
                    for x in key
                ]
            )
        )
        results = []
        for row in input:
            # If the row contains a string,
            # try to parse as a JSON object
            if isinstance(row, str):
                if row.startswith("{"):
                    row = _json.loads(row)
                else:
                    row = {}

            if isinstance(default, dict):
                row = {**default, **row}
            else:
                row = {
                    **{
                        k: default
                        for k in key.keys()
                        if (
                            "regex:" not in k.lower() and
                            "*" not in k
                        )
                    },
                    **row
                }
            rename_dict = wildcard_expansion_dict(row.keys(), key)
            results.append({
                rename_dict[k]: row.get(k, default)
                for k in rename_dict
            })
    else:
        def _get_value(value):
            """
            Get the value of a key in a dictionary or JSON dictionary
            Return the default value if the key is not found or
            if an error occurs
            """
            try:
                if isinstance(value, dict):
                    return value.get(key, default)
                elif isinstance(value, str) and value.startswith("{"):
                    return _json.loads(value).get(key, default)
                else:
                    return default
            except:
                return default
            
        results = [
            _get_value(row)
            for row in input
        ]

    if single_input:
        return results[0]
    else:
        return results
