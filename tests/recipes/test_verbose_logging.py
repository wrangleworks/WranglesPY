import pandas as pd
import wrangles
import pytest


def test_full_recipe():
    """
    Test the output of verbose logging with only wrangles
    """
    wrangles.recipe.run(
        """
          read:
            - test:
                rows: 5
                values:
                  header1: value1
                  header2: value2
          wrangles:
            - convert.case:
                case: upper
                input: header1
          write:
            - file:
                name: tests/temp/temp.csv
        """,
        log_file='tests/temp/temp.md'
    )

    with open('tests/temp/temp.md') as f:
        lines = f.readlines()

    assert (
        lines[3].startswith('## Read') and
        lines[10].startswith('## Wrangles') and
        lines[53].startswith('## Write')
    )


def test_wrangle():
    """
    Test the output of verbose logging with only wrangles
    """
    data = pd.DataFrame({
        'Col': ['Hello', 'World']
    })
    recipe = """
      wrangles:
        - convert.case:
            case: lower
            input: Col
            output: Col Lower
    """
    wrangles.recipe.run(recipe, dataframe=data, log_file='tests/temp/log-wrangle.md')

    with open('tests/temp/log-wrangle.md') as f:
        lines = f.readlines()
    assert (
        lines[5] == '## Wrangles\n' and
        lines[9] == "1. **convert.case** *['Col']* into  *Col Lower* \n"
    )

def test_read():
    """
    Test the output of verbose logging with only read
    """
    recipe = """
      read:
        - file:
            name: tests/samples/data.csv
    """
    wrangles.recipe.run(recipe, log_file='tests/temp/log-read.md')
    with open('tests/temp/log-read.md') as f:
        lines = f.readlines()
    assert (
        lines[3] == '## Read\n' and
        lines[4] == 'This recipe first reads in a  **file** with the filepath ** and a length of  rows**. \n'
    )

def test_write():
    """
    Test the output of verbose logging with only write
    """
    recipe = """
      write:
        - file:
            name: tests/samples/temp.csv
    """
    wrangles.recipe.run(recipe, log_file='tests/temp/temp.md')
    with open('tests/temp/temp.md') as f:
        lines = f.readlines()
    assert (
        lines[7] == '## Write\n' and
        lines[9] == 'The recipe writes to a  **file**  with the following parameters:\n'
    )

def test_no_output_folder():
    """
    Test the error message of a log output into a non-existent folder.
    """
    data = pd.DataFrame({
        'Col': ['Hello', 'World']
    })
    recipe = """
      wrangles:
        - convert.case:
            case: lower
            input: Col
            output: Col Lower
    """
    with pytest.raises(FileNotFoundError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data, log_file='logTests/temp.csv')
    assert info.typename == 'FileNotFoundError' and info.value.args[1] == 'No such file or directory'
