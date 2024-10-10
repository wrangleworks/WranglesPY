"""
Compare subsets of input data
"""

from collections import OrderedDict as _OrderedDict
from difflib import SequenceMatcher as _SequenceMatcher


def _ordered_words(string, char):
    """
    Generate an ordered dictionary of words from a string.
    """
    words = _OrderedDict()
    for word in string.split(char):
        if word not in words:
            words[word] = None
    return words


def _contrast(input: list, type: str ='difference', char: str = ' ') -> list:
    """
    Compare the intersection or difference between multiple strings.

    :param input: 2D list of strings to compare. [[str, str1], [str2, str3], ...]
    :param type: The type of comparison to perform. 'difference' or 'intersection'
    :param char: The character to split the strings on. Default is a space
    """
    results = []
    for row in input:
            
        if not row:
            return ""

        # Generate ordered words for each string
        ordered_words_list = [_ordered_words(x, char) for x in row]

        # Initialize intersection with the words of the first string
        common_words = _OrderedDict(ordered_words_list[0])

        if type == 'intersection':

            # Find the intersection by keeping only common words in the same order
            for words in ordered_words_list[1:]:
                common_words = _OrderedDict((k, None) for k in common_words if k in words)

            intersection = " ".join(common_words.keys())
            results.append(intersection)

        else:
            # Find the difference by keeping words that are in any string but not in the common words
            all_words_flat = _OrderedDict()
            for words in ordered_words_list:
                for word in words:
                    if word not in all_words_flat:
                        all_words_flat[word] = None

            difference = " ".join(k for k in all_words_flat if k not in common_words)
            results.append(difference)

    return results

def _overlap(
        input: list,
        non_match_char: str = '*',
        include_ratio: bool = False,
        decimal_places: int = 3,
        exact_match: str = None,
        empty_a: str = None,
        empty_b: str = None,
        all_empty: str = None,
    ) -> list:
    """
    Find the matching characters between two strings.
    return: 2D list with the matched elements or the matched elements and the ratio of similarity in a list
    """
    results = []
    for row in input:

        a_str = str(row[0])
        b_str = str(row[1])

        if not len(a_str) or not len(b_str):
            if not len(a_str) and not len(b_str):
                empty_value = all_empty
            elif not len(a_str):
                empty_value = empty_a
            else:
                empty_value = empty_b

            if include_ratio:
                results.append([empty_value, 0])
            else:
                results.append(empty_value)
            continue

        # Create a SequenceMatcher with '-' as 'junk'
        matcher = _SequenceMatcher(lambda x: x == '-', a_str, b_str)
        if matcher.ratio() == 1.0:
            if include_ratio:
                results.append(
                    [exact_match if exact_match else a_str, 0]
                )
            else:
                results.append(exact_match if exact_match else a_str)
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
