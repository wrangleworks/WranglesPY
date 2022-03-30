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