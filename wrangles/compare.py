"""
Compare subsets of input data
"""

from difflib import SequenceMatcher


    
def _contrast(input_a: list, input_b: list, type: str ='difference', char: str = ' ') -> list:
    """
    Compare the elements in two lists and return the difference or intersection
    """
    results = []
    for a, b in zip(input_a, input_b):
            
        # split the strings into lists

        compare_types = ['intersection', 'difference']

        if type not in compare_types:
            raise ValueError(f"Type must be one of {compare_types}")

        col_2 = set(b.split(char))

        # dict to hold the comparison operation
        compare_operation = {
            'intersection': lambda x: x in col_2,
            'difference': lambda x: x not in col_2
        }

        # simple techniques to get intersection and difference
        # dict.fromkeys is trick to keep the tokens in original order
        output =  list(dict.fromkeys(
            [
                word
                for word in a.split(char)
                if compare_operation[type](word)
            ]
        ))

        results.append(' '.join(output))

    return results

def _overlap(
        input_a: str,
        input_b: str,
        non_match_char: str = '*',
        include_ratio: bool = False,
        decimal_places: int = 3,
        exact_match_value: str = '<<EXACT_MATCH>>',
        input_a_empty_value: str = '<<A EMPTY>>',
        input_b_empty_value: str = '<<B EMPTY>>',
        both_empty_value: str = '<<BOTH EMPTY>>',
    ) -> list:
    """
    Find the matching characters between two strings.
    return: 2D list with the matched elements or the matched elements and the ratio of similarity in a list
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

def text(
    input_a: list,
    input_b: list,
    method: str = 'difference',
    char: str = ' ',
    non_match_char: str = '*',
    include_ratio: bool = False,
    decimal_places: int = 3,
    exact_match_value: str = '<<EXACT_MATCH>>',
    input_a_empty_value: str = '<<A EMPTY>>',
    input_b_empty_value: str = '<<B EMPTY>>',
    both_empty_value: str = '<<BOTH EMPTY>>',
) -> list:
    """
    Compare two strings and return the intersection or difference using overlap or use match to find the matching characters between two strings.

    :param input_a: List of strings to compare
    :param input_b: List of strings to compare
    :param method: The type of comparison to perform
    :param char: The character to split the strings on. Default is a space
    :param non_match_char: Character to use for non-matching characters
    :param include_ratio: Include the ratio of matching characters
    :param decimal_places: Number of decimal places to round the ratio to
    :param exact_match_value: Value to use for exact matches
    :param input_a_empty_value: Value to use for empty input a
    :param input_b_empty_value: Value to use for empty input b
    :param both_empty_value: Value to use for empty input a and b
    """

    if method not in ['difference', 'intersection', 'overlap']:
        raise ValueError(f"Method must be one of ['difference', 'intersection', 'overlap']")

    if method in ['difference', 'intersection']:
        return _contrast(input_a, input_b, method, char)
    
    if method == 'overlap':
        return _overlap(
            input_a,
            input_b,
            non_match_char,
            include_ratio,
            decimal_places,
            exact_match_value,
            input_a_empty_value,
            input_b_empty_value,
            both_empty_value,
        )
    
