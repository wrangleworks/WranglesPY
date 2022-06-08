import pandas
import re


def join_list(input_list, join_char):
    """
    Join a python list with a specified char
    """
    results = [join_char.join(x) for x in input_list]
    return results


def concatenate(data_list, concat_char):
    results = []
    for row in data_list:
        results.append(concat_char.join(row))            
    return results
    
# Super Mario Function
def split_re(input_list, split_char):
    # split char is a list of characters -> Joining them
    if isinstance(split_char, list):
        split_char = '|'.join(split_char)
    
    results = [re.split(split_char, x) for x in input_list]
    return results
    
def split(input_list, split_char, pad=False):
    if pad:
        # Pad to be as long as the longest result
        max_len = max([len(x.split(split_char)) for x in input_list])
        results = [x.split(split_char) + [''] * (max_len - len(x.split(split_char))) for x in input_list]
    else:
        results = [x.split(split_char) for x in input_list]
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


def price_breaks(df_input, header_cat, header_val):
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
    
    df_output = pandas.DataFrame(output_padded, columns=headers)
    return df_output
    

# Super Mario function
def extend_list(input_lists):
    """
    Extend list of lists to one list
    Ex: [['Hello', 'my'], ['name is', 'Fey']] -> ['Hello', 'my', 'name is', 'Fey']
    Starts with the first list
    """
    results = []
    for x in range(len(input_lists)):
        temp = [item for sublist in input_lists[x] for item in sublist]
        results.append(temp)
    
    return results

def tokenize(input):
    """
    Tokenizes everything in a list that has spaces
    Ex: ['Cookie Monster', 'Frankenstein's monster'] -> ['Cookie', 'Monster', 'Frankenstein's', 'monster']
    Ex: 'Cookie Monster -> ['Cookie', 'Monster']
    """
    
    results = []
    for item in input:
        if isinstance(item, list):
            temp1 = [x.split() for x in item]
            temp2 = [item for sublist in temp1 for item in sublist]
            results.append(temp2)
            
        elif isinstance(item, str):
            temp = list(filter(None, item.split()))
            results.append(temp)
            
    
    return results
