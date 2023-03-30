import wrangles
import pandas as pd
import pytest



def test_template_string():
    """
    Tests passing a template as string
    """
    wrangles.recipe.run(
        """
        run:
          on_start:
            - jinja:
                template:
                    string: This is a {{length}} {{type}} screwdriver
                output_file: tests/temp/temp.jinja
                context:
                    length: "3 inch"
                    type: flat head
        """
    )

    with open('tests/temp/temp.jinja') as f:
        lines = f.read()

    assert lines == 'This is a 3 inch flat head screwdriver'


def test_template_file():
    """
    Tests the output template as well as the dataframe output from that template
    """
    df = wrangles.recipe.run(
        """
        run:
          on_start:
            - jinja:
                template:
                  file: tests/samples/jinja_generic_template.jinja
                output_file: tests/temp/output_template.jinja
                context:
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

        wrangles:
            - create.jinja:
                input: data column
                output: description
                template: 
                    file: tests/temp/output_template.jinja
        """,
        dataframe = pd.DataFrame({
            'data column': [
                {'Category': 'Parts', 'size': '1/2', 'color': 'brown'},
                {'Category': 'Pieces', 'quantity': '12', 'color': 'red'}
            ]
        })
    )
    assert df['description'][0] == '\nsize: 1/2 '

def test_bad_filepath():
    """
    Tests a bad template filepath
    """
    with pytest.raises(Exception) as info:
        raise wrangles.recipe.run(
            """
            run:
              on_start:
                - jinja:
                    template:
                      file: doesn't exist
                    output_file: tests/temp/output_template.jinja
                    context:
                      placeholder: value
            """
        )
    assert info.typename == 'TemplateNotFound'

def test_no_template():
    """
    Tests the error when not given a template
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(
            """
            run:
              on_start:
                - jinja:
                    template:
                      invalid: input
                    output_file: tests/temp/output_template.jinja
                    context:
                      placeholder: value
            """
        )
    assert (
        info.typename == 'ValueError' and
        info.value.args[0][:20] == 'jinja: Either a file'
    )
