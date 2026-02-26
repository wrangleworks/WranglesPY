"""
Compare subsets of input data
"""

from collections import OrderedDict as _OrderedDict
from difflib import SequenceMatcher as _SequenceMatcher
import unicodedata
from typing import Tuple

def normalize_alphanum(text: str) -> str:
    """
    Normalizes text using Python's built-in unicodedata library.
    Maps international characters to base ASCII (e.g., ü -> u).
    Useful for standardizing strings before a comparison.
    """
    if not isinstance(text, str):
        text = str(text)
        
    text = text.lower()
    text = text.replace('ß', 'ss')
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    
    return ''.join(char for char in text if char.isalnum())


def partial_ratio(token: str, text: str) -> Tuple[float, int, int]:
    """
    Calculates the best difflib SequenceMatcher ratio for a token within a larger text string.
    Returns: (best_ratio, missing_start_count, missing_end_count)
    """
    if not token or not text: return 0.0, 0, 0
    if token in text: return 1.0, 0, 0
    
    token_len = len(token)
    text_len = len(text)
    
    if token_len >= text_len:
        # Replaced difflib.SequenceMatcher with _SequenceMatcher
        sm = _SequenceMatcher(None, token, text)
        ratio = sm.ratio()
        valid_blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
        if valid_blocks:
            longest = max(valid_blocks, key=lambda x: x.size)
            m_start = longest.a
            m_end = token_len - (longest.a + longest.size)
        else:
            m_start, m_end = 0, token_len
        return round(ratio, 2), m_start, m_end
    
    best_ratio = 0.0
    best_m_start = 0
    best_m_end = token_len
    # Add a tiny margin to the window size to account for a missing/extra character
    window_size = token_len + 2 
    
    for i in range(text_len - token_len + 1):
        window = text[i:i+window_size]
        # Replaced difflib.SequenceMatcher with _SequenceMatcher
        sm = _SequenceMatcher(None, token, window)
        r = sm.ratio()
        if r > best_ratio:
            best_ratio = r
            valid_blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
            if valid_blocks:
                longest = max(valid_blocks, key=lambda x: x.size)
                best_m_start = longest.a
                best_m_end = token_len - (longest.a + longest.size)
            else:
                best_m_start, best_m_end = 0, token_len
                
        if best_ratio == 1.0:
            break
            
    return round(best_ratio, 2), best_m_start, best_m_end


def mask_original_term(orig_t: str, missing_start: int, missing_end: int) -> str:
    """
    Replaces unmatched characters at the start and end of the original string with asterisks
    based on the missing counts calculated from the normalized matching blocks.
    """
    if missing_start == 0 and missing_end == 0:
        return orig_t
    
    chars = list(orig_t)
    
    start_idx = 0
    if missing_start > 0:
        alphanum_count = 0
        for i, c in enumerate(chars):
            if c.isalnum():
                alphanum_count += 1
            if alphanum_count == missing_start:
                start_idx = i + 1
                break
                
    end_idx = len(chars)
    if missing_end > 0:
        alphanum_count = 0
        for i in range(len(chars)-1, -1, -1):
            if chars[i].isalnum():
                alphanum_count += 1
            if alphanum_count == missing_end:
                end_idx = i
                break
                
    res = ""
    if missing_start > 0:
        res += "*" * missing_start
    
    if start_idx >= end_idx:
        return "*" * (missing_start + missing_end)
        
    res += "".join(chars[start_idx:end_idx])
    
    if missing_end > 0:
        res += "*" * missing_end
        
    return res

def _ordered_words(string, char):
    """
    Generate an ordered dictionary of words from a string.
    """
    words = _OrderedDict()
    for word in string.split(char):
        if word not in words:
            words[word] = None
    return words


def contrast(input: list, type: str ='difference', char: str = ' ', case_sensitive = True) -> list:
    """
    Compare the intersection or difference between multiple strings.

    :param input: 2D list of strings to compare. [[str, str1], [str2, str3], ...]
    :param type: The type of comparison to perform. 'difference' or 'intersection'
    :param char: The character to split the strings on. Default is a space
    :param case_sensitive: Whether the comparison is case sensitive. Default is True
    """
    results = []
    for row in input:
            
        if not row:
            return ""

        # Generate ordered words for each string
        if not case_sensitive and type != 'intersection':
            ordered_words_list = [_ordered_words(x.lower(), char) for x in row]
        else:
            ordered_words_list = [_ordered_words(x, char) for x in row]

        # Initialize intersection with the words of the first string
        common_words = _OrderedDict(ordered_words_list[0])

        if type == 'intersection':

            # Find the intersection by keeping only common words in the same order
            for words in ordered_words_list[1:]:
                # Preserve the case of words from common_words if case_sensitive is False
                if not case_sensitive:
                    words_lower = set(w.lower() for w in words)
                    common_words = _OrderedDict((k, None) for k in common_words if k.lower() in words_lower)
                else:
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

def overlap(
        input: list,
        non_match_char: str = '*',
        include_ratio: bool = False,
        decimal_places: int = 3,
        exact_match: str = None,
        empty_a: str = None,
        empty_b: str = None,
        all_empty: str = None,
        case_sensitive: bool = True
    ) -> list:
    """
    Find the matching characters between two strings.
    return: 2D list with the matched elements or the matched elements and the ratio of similarity in a list
    """
    results = []
    for row in input:

        if not case_sensitive:
            a_str = str(row[0]).lower()
            b_str = str(row[1]).lower()
        else:
            a_str = str(row[0])
            b_str = str(row[1])
        
        # To be used in output in order to preserve original casing
        a_original = str(row[0])

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
                    [exact_match if exact_match else a_str, 1]
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
            result.append(a_original[block.a:match_end_a])

            # Update the last match end indices
            last_match_end_a = match_end_a
            last_match_end_b = block.b + block.size

        if include_ratio:
            results.append([''.join(result), round(matcher.ratio(), decimal_places)])
        else:
            results.append(''.join(result))

    return results

def deduplicate(result, enabled=False, ignore_case=False):
    if not enabled:
        return result

    final = []
    seen = set()

    for item in result:
        key = str(item).lower() if ignore_case and isinstance(item, str) else item
        if key not in seen:
            seen.add(key)
            final.append(item)

    return final
