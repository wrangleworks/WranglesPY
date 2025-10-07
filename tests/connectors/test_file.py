"""
Test the file connector for reading and writing files to the local file system.
"""
import uuid as _uuid
import wrangles
import pandas as _pd
import pytest


class TestRead:
    """
    Test reading files with the file connector
    """
    def test_read_csv(self):
        """
        Test a basic .csv import
        """
        recipe = """
          read:
            file:
              name: tests/samples/data.csv
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_read_txt(self):
        """
        Test a basic .txt import
        """
        recipe = """
          read:
            file:
              name: tests/samples/data.txt
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_read_json(self):
        """
        Test a basic .json import
        """
        recipe = """
          read:
            file:
              name: tests/samples/data.json
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_read_excel(self):
        """
        Test a basic .xlsx import
        """
        recipe = """
          read:
            file:
              name: tests/samples/data.xlsx
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    ## JSON Lines
    def test_read_jsonl(self):
        recipe = """
        read:
          file:
            name: tests/samples/data.jsonl
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_read_csv_columns(self):
        """
        Test a csv import where user has selected only a subset of the columns
        """
        recipe = """
          read:
            file:
              name: tests/samples/data.csv
              columns:
                - Find
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find']

    def test_read_json_columns(self):
        """
        Test a json import where user has selected a subset of columns
        """
        recipe = """
          read:
            file:
              name: tests/samples/data.json
              columns:
                - Find
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find']

    def test_read_excel_columns(self):
        """
        Test a basic .xlsx import
        """
        recipe = """
          read:
            file:
              name: tests/samples/data.xlsx
              columns:
                - Find
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find']  

    def test_read_pickle(self):
        """
        Test reading a pickle file
        """
        filename = str(_uuid.uuid4())
        _pd.DataFrame(
            {"header1": ["value1", "value2", "value3"]}
        ).to_pickle(f"tests/temp/{filename}.pkl")

        df = wrangles.recipe.run(
            """
            read:
              - file:
                  name: tests/temp/${filename}.pkl
            """,
            variables={"filename": filename}
        )
        
        assert (
            df["header1"][0] == "value1"
            and len(df) == 3
        )

    def test_read_pickle_gzip(self):
        """
        Test reading a pickle file that's gzipped
        """
        filename = str(_uuid.uuid4())
        _pd.DataFrame(
            {"header1": ["value1", "value2", "value3"]}
        ).to_pickle(f"tests/temp/{filename}.pkl.gz")

        df = wrangles.recipe.run(
            """
            read:
              - file:
                  name: tests/temp/${filename}.pkl.gz
            """,
            variables={"filename": filename}
        )
        
        assert (
            df["header1"][0] == "value1"
            and len(df) == 3
        ) 

    def test_read_unsupported_filetype(self):
        """
        Check an appropriate error is given if the user 
        tries to read an unknown file type
        """
        with pytest.raises(ValueError, match="'jason'"):
            wrangles.recipe.run(
                """
                read:
                  - file:
                      name: data.jason
                """
            )

class TestWrite:
    """
    Test writing files with the file connector
    """
    # Write using index
    def test_write_file_indexed(self):
        recipe = """
        read:
          file:
            name: tests/samples/data.xlsx
        wrangles:
            - convert.case:
                input: Find
                case: lower
        write:
            file:
              name: tests/temp/write_data.xlsx
              index: true
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_write_file_optional_col(self):
        """
        Tests an optional column that is there
        """
        recipe = """
        read:
          file:
            name: tests/samples/data.xlsx
        wrangles:
            - convert.case:
                input: Find
                output: find
                case: lower
        write:
            file:
              name: tests/temp/write_data.xlsx
              columns:
                - Find
                - Replace
                - find?
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace', 'find']

    def test_write_file_optional_not_col(self):
        """
        Tests an optional column that is not there
        """
        recipe = """
        read:
          file:
            name: tests/samples/data.xlsx
        wrangles:
            - convert.case:
                input: Find
                output: Find
                case: lower
        write:
            file:
              name: tests/temp/write_data.xlsx
              columns:
                - Find
                - Replace
                - find?
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_write_csv(self):
        """
        Test exporting a .csv
        """
        wrangles.recipe.run(
            """
              read:
                - test:
                    rows: 5
                    values:
                      Find: aaa
                      Replace: bbb
              write:
                file:
                  name: tests/temp/temp.csv
            """
        )
        df = wrangles.recipe.run(
            """
              read:
                file:
                  name: tests/temp/temp.csv
            """
        )
        assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 5

    def test_write_txt(self):
        """
        Test exporting a .txt
        """
        wrangles.recipe.run(
            """
              read:
                - test:
                    rows: 5
                    values:
                      Find: aaa
                      Replace: bbb
              write:
                file:
                  name: tests/temp/temp.txt
            """
        )
        df = wrangles.recipe.run(
            """
              read:
                file:
                  name: tests/temp/temp.txt
            """
        )
        assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 5

    def test_write_json(self):
        """
        Test exporting a .json
        """
        wrangles.recipe.run(
            """
              read:
                - test:
                    rows: 5
                    values:
                      Find: aaa
                      Replace: bbb
              write:
                file:
                  name: tests/temp/temp.json
                  orient: records
            """
        )
        df = wrangles.recipe.run(
            """
              read:
                file:
                  name: tests/temp/temp.json
                  orient: records
            """
        )
        assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 5

    # Write a json lines file
    def test_write_jsonl(self):
        recipe = """
        read:
          file:
            name: tests/samples/data.xlsx
        wrangles:
            - convert.case:
                input: Find
                case: lower
        write:
            file:
              name: tests/temp/write_data.jsonl
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_write_unsupported_filetype(self):
        """
        # Exporting file type error message
        """
        with pytest.raises(ValueError, match="'jason'"):
            wrangles.recipe.run(
                """
                read:
                    - file:
                        name: tests/temp/temp.csv
                
                write:
                    - file:
                        name: tests/temp/data.jason
                """
            )

    # Write using index
    def test_write_with_index(self):
        recipe = """
        read:
          file:
            name: tests/samples/data.xlsx
        wrangles:
            - convert.case:
                input: Find
                case: lower
        write:
            file:
              name: tests/temp/write_data.xlsx
              index: true
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_write_pickle(self):
        """
        Test writing a pickle file
        """
        filename = str(_uuid.uuid4())
        wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 5
                  values:
                    header1: value1
            write:
              - file:
                  name: tests/temp/${filename}.pkl
            """,
            variables={"filename": filename}
        )
        df = _pd.read_pickle(f"tests/temp/{filename}.pkl")
        assert (
            df["header1"][0] == "value1"
            and len(df) == 5
        )

    def test_write_pickle_gzip(self):
        """
        Test writing a pickle file that's gzipped
        """
        filename = str(_uuid.uuid4())
        wrangles.recipe.run(
            """
            read:
              - test:
                  rows: 5
                  values:
                    header1: value1
            write:
              - file:
                  name: tests/temp/${filename}.pkl.gz
            """,
            variables={"filename": filename}
        )
        df = _pd.read_pickle(f"tests/temp/{filename}.pkl.gz")
        assert (
            df["header1"][0] == "value1"
            and len(df) == 5
        )

    def test_write_file_format_conditional(self):
        """
        Test the format function with conditional_formats
        """
        df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                col1: aaa
                col2: bbb
        write:
          - file:
              name: tests/temp/format_data.xlsx
              formatting:
                conditional_formats:
                  col1:
                    type: text
                    criteria: not containing
                    value: '123456'
                    format:
                      bg_color: '#04260D'
                      font_color: '#5AEC80'
                  col2:
                    type: text
                    criteria: containing
                    value: bbb
                    format:
                      bg_color: '#2C0224'
                      font_color: '#F73BD3'
        """
        )
        assert df.columns.tolist() == ['col1', 'col2']

    def test_write_file_format_header_format(self):
        """
        Test the format function with header_format
        """
        df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                col1: aaa
                col2: bbb
        write:
          - file:
              name: tests/temp/format_data.xlsx
              formatting:
                header_format:
                  font_name: Rastanty Cortez
                  font_size: 25
                  bold: true
                  underline: true
        """
        )
        assert df.columns.tolist() == ['col1', 'col2']

    def test_write_file_format_column_formats(self):
        """
        Test the format function with column_formats
        """
        df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                col1: aaa
                col2: bbb
        write:
          - file:
              name: tests/temp/format_data.xlsx
              formatting:
                column_formats:
                  col1:
                    font_name: Ravie
                    font_size: 30
                    bg_color: '#04260D'
                    font_color: '#5AEC80'
                  col2:
                    font_name: OCRB
                    font_size: 15
                    bg_color: '#2C0224'
                    font_color: '#F73BD3'
        """
        )
        assert df.columns.tolist() == ['col1', 'col2']

    def test_write_file_format_column_and_header_formats(self):
        """
        Test the format function with column_formats and header_format
        """
        df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                col1: aaa
                col2: bbb
        write:
          - file:
              name: tests/temp/format_data.xlsx
              formatting:
                header_format:
                  font_name: Rastanty Cortez
                  font_size: 25
                  bold: true
                  underline: true
                column_formats:
                  col1:
                    font_name: Ravie
                    font_size: 30
                    bg_color: '#04260D'
                    font_color: '#5AEC80'
                  col2:
                    font_name: OCRB
                    font_size: 15
                    bg_color: '#2C0224'
                    font_color: '#F73BD3'
        """
        )
        assert df.columns.tolist() == ['col1', 'col2']

    def test_write_file_format_wrong_columns(self):
        """
        Test the format function does not error if the columns are not in the dataframe
        """
        df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                col1: aaa
                col2: bbb
        write:
          - file:
              name: tests/temp/format_data.xlsx
              formatting:
                column_formats:
                  not_col1:
                    font_name: Ravie
                    font_size: 30
                    bg_color: '#04260D'
                    font_color: '#5AEC80'
                  not_col2:
                    font_name: OCRB
                    font_size: 15
                    bg_color: '#2C0224'
                    font_color: '#F73BD3'
        """
        )
        assert df.columns.tolist() == ['col1', 'col2']

def test_read_object():
    """
    Test reading a file passed directly into the recipe as an object
    """
    df = wrangles.recipe.run(
      """
      read:
        - file:
            name: ${file}
      """,
      variables={
        "file": {
          "name": "example.csv",
          "mimeType": "text/csv",
          "data": "Q29sMSxDb2wyCmEseApiLHkKYyx6Cg=="
        }
      }
    )
    assert len(df) == 3 and df['Col1'][0] == 'a'

def test_read_object_json():
    """
    Test reading a file passed directly into the recipe as an object
    where the variable was JSON
    """
    df = wrangles.recipe.run(
      """
      read:
        - file:
            name: ${file}
      """,
      variables={
        "file": """{
          "name": "example.csv",
          "mimeType": "text/csv",
          "data": "Q29sMSxDb2wyCmEseApiLHkKYyx6Cg=="
        }"""
      }
    )
    assert len(df) == 3 and df['Col1'][0] == 'a'
