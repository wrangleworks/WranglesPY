import wrangles
import pandas as pd
import pytest
import yaml
from wrangles.connectors import memory
from wrangles.recipe_wrangles.main import recipe as recipe_wrangle


@pytest.mark.parametrize("stage", ["read", "wrangles", "write", "run"])
@pytest.mark.parametrize("source", ["direct", "embedded", "variable", "nested"])
@pytest.mark.parametrize("path_type", ["pathlib", "pathlike"])
def test_recipe_path_objects(tmp_path, stage, source, path_type):
    """
    Recipe paths work through connectors, wrangles, and nested recipe dictionaries.
    """
    recipe_path = tmp_path / "nested café.wrgl.yml"
    recipe_path.write_text(
        (
            "read:\n"
            "  test:\n"
            "    rows: 1\n"
            "    values:\n"
            "      header1: ${value}\n"
            if stage in ("read", "run") else ""
        )
        + "wrangles:\n"
        "  - convert.case:\n"
        "      input: header1\n"
        "      case: upper\n"
        "write:\n"
        "  custom.capture: {}\n",
        encoding="utf-8"
    )

    class RecipePath:
        def __fspath__(self):
            return str(recipe_path)

    name = RecipePath() if path_type == "pathlike" else recipe_path
    data = pd.DataFrame({"header1": ["value1"]})
    expected = pd.DataFrame({"header1": ["VALUE1"]})
    captured = []

    def capture(df):
        captured.append(df.copy())

    variables = {"value": "value1"}
    if source == "direct":
        if stage == "wrangles":
            result = recipe_wrangle(
                data, name=name, variables=variables, functions=[capture]
            )
        elif stage == "write":
            result = wrangles.connectors.recipe.write(
                data, name=name, variables=variables, functions=[capture]
            )
        else:
            result = getattr(wrangles.connectors.recipe, stage)(
                name=name, variables=variables, functions=[capture]
            )
    else:
        params = {"name": name}
        if source == "variable":
            params = {"name": "${child_recipe}"}
            variables["child_recipe"] = name
        recipe = params
        for _ in range(2 if source == "nested" else 1):
            recipe = (
                {"run": {"on_start": [{"recipe": recipe}]}}
                if stage == "run"
                else {stage: [{"recipe": recipe}]}
            )
        result = wrangles.recipe.run(
            recipe, dataframe=data, variables=variables, functions=[capture]
        )
        assert params["name"] == ("${child_recipe}" if source == "variable" else name)

    if stage in ("read", "wrangles"):
        pd.testing.assert_frame_equal(result, expected)
    if stage == "wrangles":
        assert captured == []
    else:
        assert len(captured) == 1
        pd.testing.assert_frame_equal(captured[0], expected)


def test_recipe_path_serialization_keeps_safe_yaml_behavior(tmp_path):
    """
    Supporting paths does not allow arbitrary objects or change global dumpers.
    """
    with pytest.raises(ValueError, match="Recipe passed in as an invalid type"):
        wrangles.recipe.run({"read": {"recipe": {"name": object()}}})
    with pytest.raises(yaml.representer.RepresenterError):
        yaml.safe_dump({"name": tmp_path})


def test_read_recipe_connector():
    recipe = """
    read:
      - recipe:
          name: 'tests/samples/recipe_sample.wrgl.yaml'
          variables:
            inputFile: 'tests/samples/data.csv'
    """
    df = wrangles.recipe.run(recipe)
    assert df['Find2'].iloc[0] == 'brg'
    
    
# Recipe as a connector
from wrangles.connectors.recipe import read, run
def test_read_recipe_connector_2():
  recipe = """
  read:
      - recipe:
          name: 'tests/samples/recipe_sample.wrgl.yaml'
          variables:
            inputFile: 'tests/samples/data.csv'
  """
  df = read(recipe)
  assert df['Find2'].iloc[0] == 'brg'
  
# writing
def test_write_recipe_connector():
  recipe = """
  read:
      - recipe:
          name: 'tests/samples/recipe_sample.wrgl.yaml'
          variables:
            inputFile: 'tests/samples/data.csv'
  write:
      - recipe:
          name: 'tests/samples/recipe_sample.wrgl.yaml'
          variables:
            inputFile: 'tests/samples/data.csv'
  """
  df = read(recipe)
  assert df['Find2'].iloc[0] == 'brg'


# Running recipe
def test_run_recipe_connector():
  recipe = """
  run:
    on_start:
      - recipe:
          name: 'tests/samples/recipe_sample.wrgl.yaml'
          variables:
            inputFile: 'tests/samples/data.csv'
  """
  assert run(recipe) == None


def test_function_sub_recipe():
    """
    Test that custom functions are able to
    be called by sub-recipes.
    """
    main_recipe = 'tests/samples/sub_rec_main.wrgl.yaml'

    # Functions
    def read_data(columns):
        data = pd.DataFrame({
            'col1': ['mario', 'fey'],
            'col2': ['TACOS', 'RIBEYE'],
            'Not this': ['No', 'No']
        })
        return data[columns]

    def custom_func_1(df, case):
        if case == 'upper':
            df['col1'] = df['col1'].str.upper()
        else:
            df['col1'] = df['col1'].str.lower()
        return df
        
    def write_1(df, type):
        df.to_excel(f"tests/temp/excel.{type}")

    df = wrangles.recipe.run(
        recipe=main_recipe,
        functions=[
            custom_func_1,
            write_1,
            read_data,
        ]
    )
    assert df['col1'][0] == 'MARIO'

def test_read():
    """
    Test read defined within the recipe
    """
    df = wrangles.recipe.run(
        """
        read:
          - recipe:
              read:
                - test:
                    rows: 5
                    values:
                      header1: value1
              wrangles:
                - convert.case:
                    input: header1
                    case: upper
        """
    )
    assert df["header1"][0] == "VALUE1"

def test_wrangles():
    """
    Test wrangles defined within the recipe
    """
    df = wrangles.recipe.run(
        """
        read:
            - test:
                rows: 5
                values:
                    header1: value1
        wrangles:
          - recipe:
              wrangles:
                - convert.case:
                    input: header1
                    case: upper
        """
    )
    assert df["header1"][0] == "VALUE1"


def test_recipe_wrangle_in_batch_does_not_write_partial_batches():
    """
    Test that a recipe used as a wrangle does not run its own write step
    once per batch. The outer recipe should write the final combined result.
    """
    memory.clear()

    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1000
              values:
                header1: value1
        wrangles:
          - batch:
              batch_size: 100
              wrangles:
                - recipe:
                    wrangles:
                      - convert.case:
                          input: header1
                          case: upper
                    write:
                      - memory:
                          id: partial_recipe_write
        write:
          - memory:
              id: final_recipe_write
        """
    )

    assert "partial_recipe_write" not in memory.dataframes
    assert len(memory.dataframes["final_recipe_write"]["data"]) == 1000

def test_write():
    """
    Test write defined within the recipe
    """
    wrangles.recipe.run(
        """
        read:
            - test:
                rows: 5
                values:
                    header1: value1
        write:
          - recipe:
              wrangles:
                - convert.case:
                    input: header1
                    case: upper
              write:
                - memory:
                    id: recipe_write
        """
    )
    assert memory.dataframes["recipe_write"]["data"][0][0] == "VALUE1"

def test_write_optional_col():
    """
    Test write defined within the recipe with an optional column
    """
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
        wrangles:
          - convert.case:
              input: header1
              output: HEADER!
              case: upper
        write:
          - recipe:
              columns:
                - header1
                - HEADER!?
              write:
                - memory:
                    id: recipe_write
        """
    )
    assert memory.dataframes['recipe_write']['columns'] == ['header1', 'HEADER!']

def test_write_optional_no_col():
    """
    Test write defined within the recipe with an optional column that does not exist
    """
    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                header1: value1
        wrangles:
          - convert.case:
              input: header1
              case: upper
        write:
          - recipe:
              columns:
                - header1
                - HEADER!?
              write:
                - memory:
                    id: recipe_write
        """
    )
    assert memory.dataframes['recipe_write']['columns'] == ['header1']

def test_run():
    """
    Test run defined within the recipe
    """
    wrangles.recipe.run(
        """
        run:
          on_start:
          - recipe:
              read:
                - test:
                    rows: 5
                    values:
                      header1: value1
              wrangles:
                - convert.case:
                    input: header1
                    case: upper
              write:
                - memory:
                    id: recipe_run
        """
    )
    assert memory.dataframes["recipe_run"]["data"][0][0] == "VALUE1"

def test_model_id():
    """
    Test reading a recipe with a model ID
    """
    df = wrangles.recipe.run(
        """
        read:
          - recipe:
              name: 1e13e845-bc3f-4b27
        """
    )
    assert (
        len(df) == 15 and
        list(df.columns[:3]) == ["Part Number", "Description", "Brand"]
    )

def test_model_with_custom_functions():
    """
    Test a model that includes custom functions
    """
    df = wrangles.recipe.run(
        """
        read:
          - recipe:
              name: 42f319a8-0849-4177
        """
    )
    assert (
        df['header1'][0] == "value1" and
        df['header2'][0] == "value2" and
        df['header3'][0] == "VALUE2"
    )
