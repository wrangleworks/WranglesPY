import wrangles
import pandas as pd
import pytest

recipe = """
run:
  on_start:
    - jinja:
        template: ${template}
        output_file: ${output_template}
        context_dictionary:
          category_fields:

            - category: All
              cat_fields:
                - field: color

            - category: Parts
              cat_fields:
                - field: size

            - category: Pieces
              cat_fields:
                - field: quantity
"""
template = 'tests/samples/jinja_generic_template.jinja'
output_template = 'tests/samples/output_template.txt'

def test_jinja_connector():
    """
    Tests the output template as well as the dataframe output from that template
    """
    wrangles.recipe.run(recipe, variables={'template': template, 'output_template': output_template})
    output_text = pd.read_csv('tests/samples/output_template.txt')
    data = pd.DataFrame({
        'data column': [{'category': 'Parts', 'size': '1/2', 'color': 'brown'}, {'category': 'Pieces', 'quantity': '12', 'color': 'red'}]
    })
    recipe2 = """
    wrangles:
      - jinja:
          input: data column
          output: description
          template: 
            file: ${output_template}
    """
    df = wrangles.recipe.run(recipe2, dataframe=data, variables={'output_template': output_template})
    assert output_text["{% if Category == 'Parts' %}"][0] == '{% if size is defined %}size: {{ size }} {% endif %}' and list(df.columns) == ['data column', 'description']

def test_jinja_bad_filepath():
    """
    Tests a bad template filepath
    """
    template = """
    This is not a filepath
    """
    with pytest.raises(Exception) as info:
        raise wrangles.recipe.run(recipe, variables={'template': template, 'output_template': 'tests/samples/output_template.jinja'})
    assert info.typename == 'TemplateNotFound'

def test_jinja_no_template():
    """
    Tests the error when not given a template
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, variables={'output_template': 'tests/samples/output_template.jinja'})
    assert info.typename == 'ValueError' and info.value.args[0] == 'Variable ${template} was not found.'

def test_jinja_something_else():
    """
    Tests the error when not given an output_template
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, variables={'template': template})
    assert info.typename == 'ValueError' and info.value.args[0] == 'Variable ${output_template} was not found.'