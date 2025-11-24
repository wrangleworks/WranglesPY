from typing import Union as _Union
import types as _types
import re as _re
import pandas as _pandas
import numpy as _np


def flatten_lists(lst):
    return [item for sublist in lst for item in (flatten_lists(sublist) if isinstance(sublist, list) else [sublist])]


def concatenate(data_list, concat_char, skip_empty: bool=False):
    """
    Concatenate a list of columns
    """
    if skip_empty:
        return [
            concat_char.join([str(x) for x in row if x])
            if isinstance(row, (list, _np.ndarray)) else row for row in data_list
        ]
    else:
        return [
            concat_char.join([str(x) for x in row])
            if isinstance(row, (list, _np.ndarray)) else row for row in data_list
        ]


def split(
    input_list,
    output_length: int = None,
    split_char = " ",
    pad=False,
    inclusive=False,
    element: _Union[int, str] = None,
    skip_empty: bool = False,
):
    """
    Split a list of strings into lists

    :param input_list: List of strings that will be split
    :param output_length: If set, set the final output length. Requires pad = true. 
    :param split_char: The character the strings will be split on.
    :param pad: If true, pad results to be a consistent length.
    :param inclusive: If true, the split lists will include the split char.
    :param element: Slice the output lists to specific elements.
    :param skip_empty: If true, skip empty cells.
    """
    # Split as either regex or simple string
    if split_char[:6] == 'regex:':
        split_char = split_char[6:].strip()
        results = [_re.split(split_char, x) for x in input_list]
    else:
        results = [x.split(split_char) for x in input_list]
    
    if skip_empty:
        results = [[x for x in row if x.strip()] for row in results]

    if inclusive:
        # Get the split stuff
        inclusive_results = [_re.findall(split_char, x) for x in input_list]

        # 'zip' together
        merged_results = []
        for i in range(len(results)):
            temp = [None]*(len(results[i]) + len(inclusive_results[i]))
            temp[::2] = results[i]
            temp[1::2] = inclusive_results[i]
            merged_results.append(temp)
        
        results = merged_results

    # If user specified certain elements
    # then slice the results appropriately
    if element is not None:
        def _int_or_none(val):
            try:
                return int(val)
            except:
                if val:
                    raise ValueError(f"{val} is not a valid index to slice on")
                else:
                    return None

        def _list_get(lst, index, default=None):
            try:
                return lst[index]
            except IndexError:
                return default

        if ":" in str(element):
            slicer = slice(*map(_int_or_none, str(element).split(":")))
        else:
            slicer = int(element)

        results = [
            _list_get(row, slicer, "")
            for row in results
        ]

    # Pad to be as long as the longest result
    if pad:
        max_len = max([len(x) for x in results])
        results = [x + [''] * (max_len - len(x)) for x in results]
        
        if output_length is not None:
            # trimming list to appropriate output columns number
            if output_length <= max_len:
                results = [x[:output_length] for x in results]
            # if more columns than number of splits, then add '' in extra columns
            else:
                results = [
                    x + [''] * (output_length - len(x))
                    for x in results
                ] 

    return results
    

def coalesce(input_list: list) -> list:
    """
    Return the first not empty result for each row
    where each row has a list of possibilities
    """
    output_list = []
    for row in input_list:
        output_row = ''
        for value in row:
            if isinstance(value, str): value = value.strip()
            if value:
                output_row = value
                break

        output_list.append(output_row)
    return output_list


def price_breaks(df_input, header_cat, header_val): # pragma: no cover
    """
    Rearrange price breaks
    """
    output = []
    headers = []
    i = 1
    for _, row in df_input.iterrows():
        output_row = []
        for key, val in row.items():
            if val:
                output_row.append(key)
                output_row.append(val)
            if len(output_row) > len(headers):
                headers.append(header_cat + ' ' + str(i))
                headers.append(header_val + ' ' + str(i))
                i+=1
        output.append(output_row)
    
    output_padded = []
    for output_row in output:
        pad_len = len(headers) - len(output_row)
        if pad_len > 0:
            placeholder_list = ['' for i in range(pad_len)]
            output_row = output_row + placeholder_list

        output_padded.append(output_row)
    
    df_output = _pandas.DataFrame(output_padded, columns=headers)
    return df_output


def remove_duplicates(input_list: list, ignore_case: bool = False) -> list:
    """
    Remove duplicates from a list. Preserves input order.
    """
    results = []
    for row in input_list:
        # If row is a list, remove duplicates while ignoring case
        if isinstance(row, list) and ignore_case:
            seen = set()
            results.append([x for x in row if x.lower() not in seen and not seen.add(x.lower())])

        # If row is a list, remove duplicates whith case considered
        elif isinstance(row, list) and not ignore_case:
            results.append(list(dict.fromkeys(row)))
        
        # If row is a string, recursively remove duplicates and return a string while ignoring case
        elif isinstance(row, str) and ignore_case:
            seen = set()
            result = []
            for word in row.split(' '):
                if word.lower() not in seen:
                    seen.add(word.lower())
                    result.append(word)
            results.append(' '.join(result))
        
        # If row is a string, recursively remove duplicates and return a string
        elif isinstance(row, str) and not ignore_case:
            # Convert row to a list
            split_row = row.split(' ')
            # Recursion
            output = remove_duplicates([split_row])
            results.append(' '.join(output[0]))

        else:
            results.append(row) # pragma: no cover 
    
    return results

def significant_figures(input_list: list, sig_figs: int = 3) -> list:
    """
    Format digits in text or standalone to the selected significant figures
    :param input_str: The input list of values to format
    :param sig_figs: The number of significant figures to format to
    :return: The formatted string with the specified number of significant figures
    """
    
    # Convert numbers to the appropriate significant figures
    def _replace_match(match):
        number_value = float('%.{}g'.format(sig_figs) % float(match[0]))
        # if the number of significant figures is less than the length of the integer, convert to integer -> aka remove trailing zeros
        if sig_figs <= len(str(int(number_value))):
            number_value = int(number_value)
        return str(number_value)
    
    number_regex = r'(\d+\.\d+)|(\.\d+)|(\d+)|(\d+(\.\d+)?e[+-]\d+)'
    results = []
    for input in input_list:
        
        output = _re.sub(number_regex, _replace_match, str(input))
        
        # if the input is a number, preserve the data type
        if isinstance(input, float):
            output = float(output)
        if isinstance(input, int):
            output = int(output)
        
        results.append(output)

    return results

def tokenize(
    input,
    method="space",
    func=None,
    pattern=None
):
    """
    Tokenizes everything in a list that has spaces
    Ex: ['Cookie Monster', 'Frankenstein's monster'] -> ['Cookie', 'Monster', 'Frankenstein's', 'monster']
    Ex: 'Cookie Monster -> ['Cookie', 'Monster']

    :param input: The list of strings to tokenize
    :param method: The method to tokenize. Can be 'space', 'boundary' or 'boundary_ignore_space'
    :param func: A function to use to tokenize the input instead of the default methods
    :param pattern: A custom regex pattern or regex string to split the input on
    :return: The tokenized list
    """
    word_boundary_pattern = _re.compile(r"([\b\W\b])")

    def split_boundary_ignore_space(value):
        return [
            x
            for x in word_boundary_pattern.split(value)
            if x.replace(' ', '') != ''
        ]

    def split_boundary(value):
        return [
            x
            for x in word_boundary_pattern.split(value)
            if x != ''
        ]

    def split_space(value):
        return value.split()
    
    # Ensure pattern is compiled
    if pattern and not isinstance(pattern, _re.Pattern):
        pattern = _re.compile(pattern)
    def split_regex(value):
        return pattern.split(value)

    if method == "space":
        split_method = split_space
    elif method == "boundary_ignore_space":
        split_method = split_boundary_ignore_space
    elif method == "boundary":
        split_method = split_boundary
    elif isinstance(func, _types.FunctionType):
        split_method = func
    elif pattern:
        split_method = split_regex
    else:
        raise ValueError("Invalid method. Must be either 'space', 'boundary' or 'boundary_ignore_space'")

    results = [
        [
            item
            for sublist in [split_method(x) for x in item]
            for item in sublist
        ]
        if isinstance(item, list)
        else split_method(str(item))
        for item in input
    ]

    return results
