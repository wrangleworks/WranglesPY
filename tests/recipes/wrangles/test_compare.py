import wrangles
import pandas as pd
import pytest


#
# Text
#

def test_compare_text_default():
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
    assert df['output'].values.tolist() == ['Pine Black Bottom', 'Maple Orange Steel', 'Normal Blue Plastic']

def test_compare_test_difference_simple_words():
    """
    Test with simple words
    """
    data = pd.DataFrame({
    'col1': [
        'Mario',
        'Luigi',
    ],
    'col2': [
        'Super Mario',
        'Super Luigi',
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
    assert df['output'].values.tolist() == ['Super', 'Super']

def test_compare_text_intersection():
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

def test_compare_text_intersection_simple_words():
    """
    Test with simple words
    """
    data = pd.DataFrame({
    'col1': [
        'Mario',
        'Luigi',
    ],
    'col2': [
        'Super Mario',
        'Super Luigi',
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
    assert df['output'].values.tolist() == ['Mario', 'Luigi']

def test_compare_text_empty_value_second_column():
    """
    Having an empty value in second column
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

def test_compare_text_intersection_multiple_columns():
    """
    Test intersection with more than two columns
    """
    data = pd.DataFrame({
        'col1': ['mario', 'luigi', 'peach', 'toad'],
        'col2': ['super mario', 'super luigi', 'super peach', 'super toad'],
        'col3': ['mega mario', 'mega luigi', 'mega peach', 'mega toad'],
    })
    recipe = """
    wrangles:
      - compare.text:
          input:
            - col1
            - col2
            - col3
          output: output
          method: intersection
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['output'].values.tolist() == ['mario', 'luigi', 'peach', 'toad']

def test_compare_text_intersection_empty_values():
    """
    Having empty values in the columns
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
        'Super Mario',
        'Super Luigi',
        'Super Peach',
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
        method: intersection
    """
    df = wrangles.recipe.run(
        recipe=recipe,
        dataframe=data,
    )
    assert df['output'].values.tolist() == ['Mario', 'Luigi', '', '', '']

def test_compare_text_difference_multiple_columns():
    """
    Test difference with more than two columns
    """
    data = pd.DataFrame({
        'col1': ['mario', 'luigi', 'peach', 'toad'],
        'col2': ['super mario', 'super luigi', 'super peach', 'super toad'],
        'col3': ['mega mario', 'mega luigi', 'mega peach', 'mega toad'],
    })
    recipe = """
    wrangles:
      - compare.text:
          input:
            - col1
            - col2
            - col3
          output: output
          method: difference
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert all(x=='super mega' for x in df['output'].values.tolist())

def test_compare_text_difference_empty_values():
    """
    Having empty values in the columns
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
        'Super Mario',
        'Super Luigi',
        'Super Peach',
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
        method: difference
    """
    df = wrangles.recipe.run(
        recipe=recipe,
        dataframe=data,
    )
    assert df['output'].values.tolist() == ['Super', 'Super', 'Super Peach', '', '']

def test_compare_text_empty_value_first_column():
    """
    Having an empty value in the first column should return the whole value of the second column
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
    assert df['output'].values.tolist() == ['Pine Black Bottom', 'Peach Oak Wood White Marble Top Console Table']

def test_compare_text_overlap():
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

def test_compare_text_overlap_empty_values():
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
        exact_match: 'They are the same'
        empty_a: 'Empty A'
        empty_b: 'Empty B'
        all_empty: 'Both Empty'
    """
    df = wrangles.recipe.run(
        recipe=recipe,
        dataframe=data,
    )
    assert df['output'].values.tolist() == [['@@@@@Mario', 0.67], ['@@@@@Luigi', 0.67], ['Empty A', 0], ['Empty B', 0], ['Both Empty', 0]]

def test_compare_overlap_default_settings():
    """
    Using overlap method and using the default empty values
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
    """
    df = wrangles.recipe.run(
        recipe=recipe,
        dataframe=data,
    )
    assert df['output'].values.tolist() == ['*****Mario', '*****Luigi', '', '', '']