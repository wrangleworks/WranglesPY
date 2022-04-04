def highest_confidence(data_list):
    results = []
    for row in data_list:
        highest_confidence = 0
        highest_result = None
        for cell in row:
            if float(cell[1]) > highest_confidence:
                highest_result = cell
                highest_confidence = float(cell[1])

        results.append(highest_result)
        
    return results

def confidence_threshold(list_1, list_2, threshold):
    results = []
    
    
    for cell_1, cell_2 in zip(list_1, list_2):
        if cell_1 == None:
            results.append(cell_2)
        elif float(cell_1[1]) > threshold:
            results.append(cell_1[0])
        else:
            results.append(cell_2)
            
    return results

def list_element(input, n):
    return [row[n] for row in input]