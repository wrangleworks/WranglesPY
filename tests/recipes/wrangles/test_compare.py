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