"""
Select subsets of input data
"""
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


def list_element(input, n, fill_value):
    """
    Select a numbered element of a list (zero indexed).
    """
    def check_if_possible(element, index):
        try:
            return element[index]
        except IndexError:
            return fill_value
        
    return [check_if_possible(row, n) if isinstance(row, list) else fill_value for row in input]


def dict_element(input, key):
    """
    Select a named element of a dictionary
    """
    return [row.get(key, '') if isinstance(row, dict) else '' for row in input]
   