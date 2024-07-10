import wrangles
import pandas as pd
import pytest


#
# Text
#

def test_text_1():
    """
    Test normal Compare Text. Difference (default)
    """
    data = pd.DataFrame({
    'col1': [
        'Mario Oak Wood White Marble Top Bookshelf',
        'Luigi Oak Wood White Marble Top Coffee Table',
        'Peach Oak Wood White Marble Top Console Table',
    ],
    'col2': [
        'Mario Pine Wood Black Marble Bottom Bookshelf',
        'Luigi Maple Wood Orange Steel Top Coffee Table',
        'Peach Normal Wood Blue Plastic Top Console Table',
    ]
    })

    recipe = """
    wrangles:
    - compare.text:
        input:
          - col1
          - col2
        output: output
        method: difference
    """

    df = wrangles.recipe.run(
        recipe=recipe,
        dataframe=data,
    )
    assert df['output'].values.tolist() == ['Oak White Top', 'Oak White Marble', 'Oak White Marble']

def test_text_2():
    """
    Test normal Compare Text. Intersection
    """
    data = pd.DataFrame({
    'col1': [
        'Mario Oak Wood White Marble Top Bookshelf',
        'Luigi Oak Wood White Marble Top Coffee Table',
        'Peach Oak Wood White Marble Top Console Table',
    ],
    'col2': [
        'Mario Pine Wood Black Marble Bottom Bookshelf',
        'Luigi Maple Wood Orange Steel Top Coffee Table',
        'Peach Normal Wood Blue Plastic Top Console Table',
    ]
    })

    recipe = """
    wrangles:
    - compare.text:
        input:
          - col1
          - col2
        output: output
        method: intersection
    """

    df = wrangles.recipe.run(
        recipe=recipe,
        dataframe=data,
    )
    assert df['output'].values.tolist() == ['Mario Wood Marble Bookshelf', 'Luigi Wood Top Coffee Table', 'Peach Wood Top Console Table']

def test_text_3():
    """
    Having an empty value in input_b
    """
    data = pd.DataFrame({
    'col1': [
        'Mario Oak Wood White Marble Top Bookshelf',
        'Peach Oak Wood White Marble Top Console Table',
    ],
    'col2': [
        'Mario Pine Wood Black Marble Bottom Bookshelf',
        '',
    ]
    })

    recipe = """
    wrangles:
    - compare.text:
        input:
          - col1
          - col2
        output: output
        method: intersection
    """

    df = wrangles.recipe.run(
        recipe=recipe,
        dataframe=data,
    )
    assert df['output'].values.tolist() == ['Mario Wood Marble Bookshelf', '']

def test_text_4():
    """
    Having an empty value in input_a
    """
    data = pd.DataFrame({
    'col1': [
        'Mario Oak Wood White Marble Top Bookshelf',
        '',
    ],
    'col2': [
        'Mario Pine Wood Black Marble Bottom Bookshelf',
        'Peach Oak Wood White Marble Top Console Table',
    ]
    })

    recipe = """
    wrangles:
    - compare.text:
        input:
          - col1
          - col2
        output: output
    """

    df = wrangles.recipe.run(
        recipe=recipe,
        dataframe=data,
    )
    assert df['output'].values.tolist() == ['Oak White Top', '']

def test_text_5():
    """
    Using overlap method
    """
    data = pd.DataFrame({
    'col1': [
        'Mario',
        'Luigi',
    ],
    'col2': [
        'SuperMario',
        'SuperLuigi',
    ]
    })

    recipe = """
    wrangles:
    - compare.text:
        input:
          - col1
          - col2
        output: output
        method: overlap
    """
    df = wrangles.recipe.run(
        recipe=recipe,
        dataframe=data,
    )
    assert df['output'].values.tolist() == ['*****Mario', '*****Luigi']

def test_text_6():
    """
    Using overlap method and having empty values
    """
    data = pd.DataFrame({
    'col1': [
        'Mario',
        'Luigi',
        '',
        'Bowser',
        ''
    ],
    'col2': [
        'SuperMario',
        'SuperLuigi',
        'SuperPeach',
        '',
        ''
    ]
    })

    recipe = """
    wrangles:
    - compare.text:
        input:
          - col1
          - col2
        output: output
        method: overlap
        non_match_char: '@'
        include_ratio: True
        decimal_places: 2
        exact_match_value: 'They are the same'
        input_a_empty_value: 'Empty A'
        input_b_empty_value: 'Empty B'
        both_empty_value: 'Both Empty'
    """
    df = wrangles.recipe.run(
        recipe=recipe,
        dataframe=data,
    )
    assert df['output'].values.tolist() == [['@@@@@Mario', 0.67], ['@@@@@Luigi', 0.67], ['Empty A', 0], ['Empty B', 0], ['Both Empty', 0]]