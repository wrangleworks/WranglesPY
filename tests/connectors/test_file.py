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

    def test_write_file_format_named_columns(self):
        """
        Test the format function with named columns
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
          file:
            name: tests/temp/format_data.xlsx
            formatting:
              font: Edwardian Script ITC
              font_size: 15
              columns:
                col1:
                  width: 10
                  header_fill_color: blue
                  font_size: 22
                col2:
                  width: 20
                  header_fill_color: '#6565bf'
                  font_size: 11
        """
        )
        assert df.columns.tolist() == ['col1', 'col2']

    def test_write_file_format_default(self):
        """
        Test the format function with defualt/general parameters
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
          file:
            name: tests/temp/format_data.xlsx
            formatting:
              font: Edwardian Script ITC
              font_size: 15
              header_fill_color: red
              width: 40
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
          file:
            name: tests/temp/format_data.xlsx
            formatting:
              columns:
                Non Existent Column:
                  width: 10
                  header_fill_color: blue
                  font_size: 22
                This column does not exist:
                  width: 20
                  header_fill_color: '#6565bf'
                  font_size: 11
              font: Edwardian Script ITC
              header_fill_color: red
              table_style: TableStyleDark3
        """
        )
        assert df.columns.tolist() == ['col1', 'col2']

    def test_write_file_format_comma_separated(self):
        """
        Test the format function with comma separated columns
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
          file:
            name: tests/temp/format_data.xlsx
            formatting:
              columns:
                col1, col2:
                  width: 10
                  header_fill_color: blue
                  font_size: 22
        """
        )
        assert df.columns.tolist() == ['col1', 'col2']

    def test_write_file_format_comma_column_name(self):
        """
        Test the format function with commas in column names
        """
        df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 5
              values:
                col1, col1, col1: aaa
                col2: bbb
        write:
          file:
            name: tests/temp/format_data.xlsx
            formatting:
              columns:
                col1\, col1\, col1:
                  width: 10
                  header_fill_color: blue
                  font_size: 22
        """
        )
        assert df.columns.tolist() == ['col1, col1, col1', 'col2']

