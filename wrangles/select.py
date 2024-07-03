from difflib import SequenceMatcher

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

def find_match(
        input_a: str,
        input_b: str,
        non_match_char: str = '*',
        include_ratio: bool = False,
        decimal_places: int = 3,
        exact_match_value: str = '<<EXACT_MATCH>>',
        input_a_empty_value: str = '<<A EMPTY',
        input_b_empty_value: str = '<<B EMPTY>>',
        both_empty_value: str = '<<BOTH EMPTY>>',
    ) -> _Union[list, str]:
    """
    Find the matching characters between two strings.
    return: 2D list with the matched elements and the ratio of similarity
    """
    results = []
    for a_value, b_value in zip(input_a, input_b):

        a_str = str(a_value)
        b_str = str(b_value)

        if not len(a_str) or not len(b_str):
            if not len(a_str) and not len(b_str):
                empty_value = both_empty_value
            elif not len(a_str):
                empty_value = input_a_empty_value
            else:
                empty_value = input_b_empty_value

            if include_ratio:
                results.append([empty_value, 0])
            else:
                results.append(empty_value)
            continue

        # Create a SequenceMatcher with '-' as 'junk'
        matcher = SequenceMatcher(lambda x: x == '-', a_str, b_str)
        if matcher.ratio() == 1.0:
            if include_ratio:
                results.append([exact_match_value,0])
            else:
                results.append(exact_match_value)
            continue

        result = []
        # Starting index for the next unmatched block in both strings
        last_match_end_a = 0
        last_match_end_b = 0

        # Iterate through the matching blocks
        for block in matcher.get_matching_blocks():
            # Handle the non-matching part
            while last_match_end_a < block.a or last_match_end_b < block.b:
                char_a = a_str[last_match_end_a] if last_match_end_a < len(a_str) else None
                char_b = b_str[last_match_end_b] if last_match_end_b < len(b_str) else None
                # These are the junk chars
                if char_a == '-' or char_b == '-':
                    result.append('') # junk replacement
                else:
                    result.append(non_match_char) # non-matching replacement

                if last_match_end_a < len(a_str): last_match_end_a += 1
                if last_match_end_b < len(b_str): last_match_end_b += 1

            # Add the matched part
            match_end_a = block.a + block.size
            result.append(a_str[block.a:match_end_a])

            # Update the last match end indices
            last_match_end_a = match_end_a
            last_match_end_b = block.b + block.size

        if include_ratio:
            results.append([''.join(result), round(matcher.ratio(), decimal_places)])
        else:
            results.append(''.join(result))

    return results