import pandas


def join_list(input_list, join_char):
    """
    Join a python list using 
    """
    results = [join_char.join(x) for x in input_list]
    return results


def concatenate(data_list, concat_char):
    results = []
    for row in data_list:
        results.append(concat_char.join(row))            
    return results


def split(input_list, split_char):
    results = [x.split(split_char) for x in input_list]
    return results


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