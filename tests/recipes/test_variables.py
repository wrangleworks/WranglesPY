"""
Test variables that are passed to recipes

Variables are defined in the form ${my_variable}
"""
import wrangles
import pandas as pd
import pytest
import platform


# recipe as a templated value
def test_templated_values_1():
    case_var = "upper"
    inputs = ['col', 'col2']
    templated_rec = """
        convert.case:
          input:
            ${inputs}
          output:
            - out
            - out2
          case: ${case_value}
    """
    data = pd.DataFrame({
        'col': ['Hello World'],
        'col2': ['hello world'],
    })
    recipe = """
    wrangles:
      - ${wrgl1}
    """
    vars = {
        'wrgl1': templated_rec,
        'case_value': case_var,
        'inputs': inputs,
    }
    df = wrangles.recipe.run(recipe, variables=vars, dataframe=data)
    assert df.iloc[0]['out'] == "HELLO WORLD"
    
    
# templated value in a sql command
def test_templated_values_2():
    data = pd.DataFrame({
        'col': ['Hello SQL']
    })
    templated_sql = """
    SELECT * from df
    """
    recipe = """
    wrangles:
      - sql: 
          command: ${sql_command}
    """
    vars = {
        "sql_command": templated_sql,
    }
    df = wrangles.recipe.run(recipe, variables=vars, dataframe=data)
    assert 1

def test_templated_valued_3():
    data = pd.DataFrame({
        'col': ['Hello World']
    })
    templated_case = "case"
    vars = {
        "tmpl_value": templated_case
    }
    recipe = """
    wrangles:
      - convert.case:
          input: col
          output: out
          ${tmpl_value}: upper
    """
    df = wrangles.recipe.run(recipe, dataframe=data, variables=vars)
    assert df.iloc[0]['out'] == 'HELLO WORLD'
 

def test_within_string():
    """
    Test that a variable within a string works.
    Test at start, middle and end.
    """
    recipe = """
    read:
      - test:
          rows: 1
          values:
            col1: value-${var}
            col2: ${var}-value
            col3: value-${var}-value
    """
    df = wrangles.recipe.run(recipe, variables={'var': '1'})
    assert (
        df.iloc[0]['col1'] == 'value-1'
        and df.iloc[0]['col2'] == '1-value'
        and df.iloc[0]['col3'] == 'value-1-value'
    )

def test_within_string_integer():
    """
    Test that a variable within a string works.
    Test at start, middle and end.
    Test with a non-string type.
    """
    recipe = """
    read:
      - test:
          rows: 1
          values:
            col1: value-${var}
            col2: ${var}-value
            col3: value-${var}-value
    """
    df = wrangles.recipe.run(recipe, variables={'var': 1})
    assert (
        df.iloc[0]['col1'] == 'value-1'
        and df.iloc[0]['col2'] == '1-value'
        and df.iloc[0]['col3'] == 'value-1-value'
    )

def test_json():
    """
    Test that a variable passed in 
    as JSON is interpreted correctly
    """
    recipe = """
    read:
      - test:
          rows: 1
          values: ${json}
    """
    df = wrangles.recipe.run(
        recipe,
        variables={'json': '{"col1":"value1","col2":"value2"}'}
    )
    assert (
        df.iloc[0]['col1'] == 'value1'
        and df.iloc[0]['col2'] == 'value2'
    )

def test_similar_to_json():
    """
    Test that a variable passed 
    in that looks like JSON but isn't
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                column1: ${not_json}
        """,
        variables={'not_json': '{{something}}'}
    )
    assert df['column1'][0] == '{{something}}'

# USER OMITS VARIABLES
def test_missing_error():
    """
    Test that the user gets a sensible error message
    if they've specified a variable that is not found
    """
    recipe = """
    read:
      - file:
          name: ${missing}
    """
    with pytest.raises(ValueError) as info:
        wrangles.recipe.run(recipe)
    assert (
        info.typename == 'ValueError' 
        and info.value.args[0] == 'Variable ${missing} was not found.'
    )

def test_missing_within_string_error():
    """
    Test that the user gets a sensible error message
    if they've specified a variable that is not found
    where the variable is within a string
    """
    recipe = """
    read:
      - file:
          name: file-${missing}.xlsx
    """
    with pytest.raises(ValueError) as info:
        wrangles.recipe.run(recipe)
    assert (
        info.typename == 'ValueError' 
        and info.value.args[0] == 'Variable ${missing} was not found.'
    )


def test_passed_as_parameter():
    """
    Test that a variable passed as
    a parameter is accessed correctly
    """
    recipe = """
    read:
      - test:
          rows: 1
          values:
            header: ${var}
    """
    df = wrangles.recipe.run(
        recipe,
        variables={'var': 'value'}
    )
    assert df.iloc[0]['header'] == 'value'


def test_passed_as_environment_variable():
    """
    Test that a variable passed as an
    environment variable is accessed correctly
    """
    if platform.system() == 'Windows':
        recipe = """
          read:
            - test:
                rows: 1
                values:
                  header: ${USERNAME}
        """
    else:
        recipe = """
          read:
            - test:
                rows: 1
                values:
                  header: ${HOME}
        """

    df = wrangles.recipe.run(recipe)
    assert len(df.iloc[0]['header']) > 0


def test_parameter_overrides_environment():
    """
    Test that a variable passed as
    a parameter overrides one that exists
    as an environment variable
    """
    if platform.system() == 'Windows':
        recipe = """
          read:
            - test:
                rows: 1
                values:
                  header: ${USERNAME}
        """
    else:
        recipe = """
          read:
            - test:
                rows: 1
                values:
                  header: ${HOME}
        """
    df = wrangles.recipe.run(
        recipe,
        variables={'HOME':'success', 'USERNAME':'success'}
    )
    assert df.iloc[0]['header'] == 'success'

def test_empty_string_value():
    """
    Test that a variable with the value set as
    an empty string is interpreted correctly
    """
    df = wrangles.recipe.run(
        """
        read:
        - test:
            rows: 1
            values:
                header: ${empty}
        """,
        variables={'empty': ''}
    )
    assert df['header'][0] == ''

def test_zero_value():
    """
    Test that a variable with the value set as
    zero is interpreted correctly
    """
    df = wrangles.recipe.run(
        """
        read:
        - test:
            rows: 1
            values:
                header: ${empty}
        """,
        variables={'empty': 0}
    )
    assert df['header'][0] == 0

def test_none_value():
    """
    Test that a variable with the value set as
    None is interpreted correctly
    """
    df = wrangles.recipe.run(
        """
        read:
        - test:
            rows: 1
            values:
                header: ${empty}
        """,
        variables={'empty': None}
    )
    assert df['header'][0] is None

def test_false_value():
    """
    Test that a variable with the value set as
    False is interpreted correctly
    """
    df = wrangles.recipe.run(
        """
        read:
        - test:
            rows: 1
            values:
                header: ${empty}
        """,
        variables={'empty': False}
    )
    assert df['header'][0] == False

def test_variables_variable():
    """
    Test that the variables variable is working
    """
    df = wrangles.recipe.run(
        """
        read:
        - test:
            rows: 1
            values:
                vars: ${recipe_variables}
        """
    )
    assert isinstance(df['vars'][0], dict)

def test_variables_variable_overwrite():
    """
    Test that a recipe_variables variable is overwritten
    """
    df = wrangles.recipe.run(
        """
        read:
        - test:
            rows: 1
            values:
                vars: ${recipe_variables}
        """,
        variables={'recipe_variables': 'This is a string'}
    )
    assert isinstance(df['vars'][0], dict)


def test_applied_permission_group_variable_explicit(monkeypatch):
    """
    Test that an explicitly-passed applied_permission_group is available as
    a recipe variable for a non-model_id recipe (there is no server-side
    default to fall back to in that case).
    """
    df = wrangles.recipe.run(
        """
        read:
        - test:
            rows: 1
            values:
                group: ${applied_permission_group}
        """,
        variables={"applied_permission_group": "enterprise"}
    )

    assert df['group'][0] == 'enterprise'


def test_applied_permission_group_variable_if(monkeypatch):
    """
    Test that applied_permission_group can be used in Python-style if conditions.
    """
    df = wrangles.recipe.run(
        """
        read:
        - test:
            rows: 1
            values:
                result: kept
        wrangles:
        - create.column:
            output: allowed
            value: true
            if: applied_permission_group == 'enterprise'
        """,
        variables={"applied_permission_group": "enterprise"}
    )

    assert df['allowed'][0] == True


def test_applied_permission_group_variable_from_recipe_metadata(monkeypatch):
    """
    Test that recipe metadata permission group is preferred for remote recipes.
    """
    monkeypatch.setattr(
        wrangles.recipe._data,
        "model",
        lambda model_id: {
            "purpose": "recipe",
            "production_version_id": "v1",
            "applied_permission_group": "metadata-group",
        }
    )
    # No model claim available - the metadata-derived value above should be
    # left untouched rather than overridden.
    monkeypatch.setattr(wrangles.recipe._data, "model_claim", lambda model_id: {})
    monkeypatch.setattr(
        wrangles.recipe._data,
        "model_content",
        lambda model_id, version_id=None: {
            "recipe": """
            read:
            - test:
                rows: 1
                values:
                    group: ${applied_permission_group}
            """
        }
    )

    df = wrangles.recipe.run("12345678-1234-1234")

    assert df["group"][0] == "metadata-group"


def test_applied_permission_group_variable_metadata_overrides_explicit(monkeypatch, caplog):
    """
    A model_id-addressed recipe's real permission group (resolved
    server-side from the model's metadata) must override an explicit
    variables={"applied_permission_group": ...} too - otherwise a caller
    could simply claim a higher role than the model's database actually
    grants them.
    """
    monkeypatch.setattr(
        wrangles.recipe._data,
        "model",
        lambda model_id: {
            "purpose": "recipe",
            "production_version_id": "v1",
            "applied_permission_group": "editor",
        }
    )
    # No model claim available - only the metadata-derived override (from
    # data.model above) is exercised by this test.
    monkeypatch.setattr(wrangles.recipe._data, "model_claim", lambda model_id: {})
    monkeypatch.setattr(
        wrangles.recipe._data,
        "model_content",
        lambda model_id, version_id=None: {
            "recipe": """
            read:
            - test:
                rows: 1
                values:
                    group: ${applied_permission_group}
            """
        }
    )

    with caplog.at_level("WARNING"):
        df = wrangles.recipe.run(
            "12345678-1234-1234",
            variables={"applied_permission_group": "admin"}
        )

    assert df["group"][0] == "editor"
    assert "does not match this model's actual permission group" in caplog.text


def test_applied_permission_level_variable_from_model_claim(monkeypatch):
    """
    Test that applied_permission_level is filled from the model claim's role
    when running a model_id directly, e.g. from Python.
    """
    monkeypatch.setattr(
        wrangles.recipe._data,
        "model",
        lambda model_id: {"purpose": "recipe", "production_version_id": "v1"}
    )
    monkeypatch.setattr(
        wrangles.recipe._data,
        "model_claim",
        lambda model_id: {
            "model_id": model_id,
            "role": "viewer",
            "applied_group": "Dev (WrangleWorks)",
        }
    )
    monkeypatch.setattr(
        wrangles.recipe._data,
        "model_content",
        lambda model_id, version_id=None: {
            "recipe": """
            read:
            - test:
                rows: 1
                values:
                    level: ${applied_permission_level}
                    group: ${applied_permission_group}
            """
        }
    )

    df = wrangles.recipe.run("12345678-1234-1234")

    assert df["level"][0] == "viewer"
    assert df["group"][0] == "Dev (WrangleWorks)"


def test_applied_permission_level_variable_claim_overrides_explicit(monkeypatch, caplog):
    """
    Like applied_permission_group, an explicit
    variables={"applied_permission_level": ...} must not let a caller claim
    a higher role than the model claim actually grants - run(model,
    variables={"applied_permission_level": "admin"}) when the real claim
    says "viewer" must use "viewer".
    """
    monkeypatch.setattr(
        wrangles.recipe._data,
        "model",
        lambda model_id: {"purpose": "recipe", "production_version_id": "v1"}
    )
    monkeypatch.setattr(
        wrangles.recipe._data,
        "model_claim",
        lambda model_id: {
            "model_id": model_id,
            "role": "viewer",
            "applied_group": "Dev (WrangleWorks)",
        }
    )
    monkeypatch.setattr(
        wrangles.recipe._data,
        "model_content",
        lambda model_id, version_id=None: {
            "recipe": """
            read:
            - test:
                rows: 1
                values:
                    level: ${applied_permission_level}
            """
        }
    )

    with caplog.at_level("WARNING"):
        df = wrangles.recipe.run(
            "12345678-1234-1234",
            variables={"applied_permission_level": "admin"}
        )

    assert df["level"][0] == "viewer"
    assert "does not match this model's actual permission level" in caplog.text


def test_model_claim_failure_does_not_block_recipe_load(monkeypatch, caplog):
    """
    A failure resolving the model claim (e.g. network issue) must not block
    the recipe from loading - applied_permission_level is simply left unset.
    """
    monkeypatch.setattr(
        wrangles.recipe._data,
        "model",
        lambda model_id: {"purpose": "recipe", "production_version_id": "v1"}
    )

    def _raise(model_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(wrangles.recipe._data, "model_claim", _raise)
    monkeypatch.setattr(
        wrangles.recipe._data,
        "model_content",
        lambda model_id, version_id=None: {
            "recipe": """
            read:
            - test:
                rows: 1
                values:
                    result: kept
            """
        }
    )

    with caplog.at_level("WARNING"):
        df = wrangles.recipe.run("12345678-1234-1234")

    assert df["result"][0] == "kept"
    assert "Could not resolve model claim" in caplog.text
