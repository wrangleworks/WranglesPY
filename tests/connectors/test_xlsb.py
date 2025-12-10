import os
import wrangles
import pytest
import pandas as _pd


class TestXLSBConnector:

    def test_read_xlsb_not_found(self):
        """
        Test error when .xlsb file doesn't exist
        """
        with pytest.raises(FileNotFoundError):
            wrangles.recipe.run(
                """  
            read:  
              - xlsb:  
                  name: non_existent_file.xlsb  
            """
            )

    def test_read_xlsb_invalid_sheet_name(self):
        """
        Test error with invalid sheet name
        """

        with pytest.raises(
            ValueError, match="xlsb - Worksheet named 'NonExistentSheet' not found"
        ):
            wrangles.recipe.run(
                f"""  
          read:  
            - xlsb:  
                name: tests/samples/data3.xlsb  
                sheet_name: NonExistentSheet  
          """
            )

    def test_read_xlsb_invalid_sheet_index(self):
        """
        Test error with invalid sheet index
        """
        with pytest.raises(ValueError, match="xlsb - Worksheet index 127 is invalid"):
            wrangles.recipe.run(
                f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb  
              sheet_name: 127
        """
            )

    def test_read_xlsb_empty_file(self):
        """
        Test reading empty file (0 rows, 0 columns)
        """
        df = wrangles.recipe.run(
            f"""  
        read:  
          - xlsb:  
              name: tests/samples/empty.xlsb   
        """
        )
        assert len(df) == 0
        assert len(df.columns) == 0

    def test_read_xlsb_non_existent_mandatory_columns(self):
        """
        Test error when requesting non-existent mandatory columns with context
        """
        with pytest.raises(KeyError) as exc_info:
            wrangles.recipe.run(
                f"""  
            read:  
              - xlsb:  
                  name: tests/samples/data3.xlsb  
                  sheet_name: Basic
                  columns:  
                    - NonExistentColumn  
            """
            )
        assert r"Failed to read XLSB file" in str(
            exc_info.value
        )

    def test_read_xlsb_non_existent_optional_columns(self):
        """
        Test error when requesting non-existent optional columns with context
        """
        df = wrangles.recipe.run(
            f"""  
            read:  
              - xlsb:  
                  name: tests/samples/data3.xlsb  
                  sheet_name: Basic
                  columns:  
                    - NonExistentColumn?
                    - Find
            """
        )
        assert df.columns.tolist() == ["Find"]

    def test_read_xlsb_no_headers(self):
        """
        Test reading file with no headers (header=None)
        """

        df = wrangles.recipe.run(
            f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: NoHeaders
              header: null  
        """
        )
        assert df.columns.tolist() == [0, 1]
        assert len(df) == 2

    def test_read_xlsb_no_headers_with_names(self):
        """
        Test reading file with no headers but providing custom names
        """

        df = wrangles.recipe.run(
            f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: NoHeaders
              header: null  
              names:  
                - CustomCol1  
                - CustomCol2  
        """
        )
        assert df.columns.tolist() == ["CustomCol1", "CustomCol2"]
        assert len(df) == 2

    def test_read_xlsb_wrong_file_extension(self):
        """
        Test that file without .xlsb extension raises appropriate error
        """

        with pytest.raises(ValueError, match="File must have .xlsb extension"):
            wrangles.recipe.run(
                f"""  
            read:  
              - xlsb:  
                  name: tests/samples/data.txt  
            """
            )

    def test_read_xlsb_sheet_list_with_invalid_sheet(self):
        """
        Test error when list contains non-existent sheet
        """
        with pytest.raises(
            ValueError, match="xlsb - Worksheet named 'NonExistent' not found"
        ):
            wrangles.recipe.run(
                f"""  
            read:  
              - xlsb:  
                  name: tests/samples/data3.xlsb  
                  sheet_name:  
                    - Basic  
                    - NonExistent  
            """
            )

    def test_read_xlsb_basic_functionality(self):
        """
        Test basic .xlsb import with common parameters
        """

        recipe = """  
          read:  
            - xlsb:  
                name: tests/samples/data3.xlsb  
                sheet_name: Basic
                columns:  
                  - Find  
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ["Find"]

    def test_read_xlsb_sheet_and_header_options(self):
        """
        Test sheet selection and header parameters together
        """

        # Test sheet name and header together
        recipe = """  
          read:  
            - xlsb:  
                name: tests/samples/data3.xlsb  
                sheet_name: 0  
                header: 0  
                skiprows: 0  
        """
        df = wrangles.recipe.run(recipe)
        assert len(df) > 0
        assert df.columns.tolist() == ['Col0', 'Col1', 'Col2']

    def test_read_xlsb_special_character_in_columns(self):
        """
        Test reading .xlsb file with special characters in column names
        """

        # Test sheet name and header together
        recipe = """  
          read:  
            - xlsb:  
                name: tests/samples/data3.xlsb  
                sheet_name: SpecialCharacters  
        """
        df = wrangles.recipe.run(recipe)

        expected_columns = [
            "Col With Spaces",
            "Col-With-Dashes",
            "Col_With_Underscores",
            "Col.With.Dots",
            "Col(With)Parentheses",
            "Col[With]Brackets",
            "Col{With}Braces",
            "Col#With#Hash",
            "Col@With@At",
            "Col$With$Dollar",
            "Col%With%Percent",
            "Col^With^Caret",
            "Col&With&Ampersand",
            "Col*With*Asterisk",
            "Col+With+Plus",
            "Col=With=Equals",
            "Col|With|Pipe",
            "Col\\With\\Backslash",
            "Col/With/Slash",
            "Col?With?Question",
            "Col<With>Brackets",
            'Col"With"Quotes',
            "Col'With'Apostrophes",
            "Col`With`Backticks",
            "Col~With~Tilde",
            "Col!With!Exclamation",
        ]

        assert df.columns.tolist() == expected_columns
        assert len(df) == 2

    def test_read_xlsb_special_characters_with_wildcard(self):
        """
        Test reading XLSB with wildcard selection on columns with special characters
        """

        # Test wildcard with spaces
        recipe = f"""  
        read:  
        - xlsb:  
            name: tests/samples/data3.xlsb  
            sheet_name: WildcardCols
            columns:  
                - Col With Spaces*  
        """
        df = wrangles.recipe.run(recipe)

        assert df.columns.tolist() == ["Col With Spaces 1", "Col With Spaces 2"]

    def test_read_xlsb_only_headers(self):
        """
        Test file with only headers (0 data rows)
        """
        df = wrangles.recipe.run(
            f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: HeadersOnly
        """
        )
        assert len(df) == 0
        assert df.columns.tolist() == ["Col1", "Col2", "Col3"]

    def test_read_xlsb_duplicate_columns(self):
        """
        Test file with duplicate column names
        """
        df = wrangles.recipe.run(
            f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: Duplicates 
        """
        )

        assert len(df.columns) == 4
        assert df.columns.tolist() == ["Name", "Age", "Name.1", "City"]

    def test_read_xlsb_mixed_data_types(self):
        """
        Test reading XLSB with mixed data types in columns
        """
        # Test reading with default dtype (object)
        recipe = f"""  
        read:  
            - xlsb:  
                name: tests/samples/data3.xlsb 
                sheet_name: MixedTypes
        """
        df = wrangles.recipe.run(recipe)

        # Verify mixed types are preserved as object dtype
        assert df["mixed_column"].dtype == "object"
        assert df["mixed_dates"].dtype == "object"

        # Check specific values are preserved
        assert df["mixed_column"].iloc[0] == "text"
        assert df["mixed_column"].iloc[1] == 123
        assert df["mixed_column"].iloc[2] == 45.67
        assert df["mixed_column"].iloc[3] == True

        # Test reading with explicit dtype specification
        recipe_str = f"""  
        read:  
            - xlsb:  
                name: tests/samples/data3.xlsb  
                sheet_name: MixedTypes
                dtype:  
                    mixed_column: str  
                    numbers_only: float  
                    text_only: str  
        """
        df_str = wrangles.recipe.run(recipe_str)

        # Verify types are converted
        assert df_str["mixed_column"].dtype == "object"  # Strings in pandas are object
        assert df_str["numbers_only"].dtype == "float64"
        assert df_str["text_only"].dtype == "object"

        # Check conversion worked
        assert df_str["mixed_column"].iloc[1] == "123"  # Number converted to string
        assert df_str["mixed_column"].iloc[2] == "45.67"  # Float converted to string

    def test_read_xlsb_mixed_types_with_na(self):
        """
        Test reading XLSB with mixed types including NA values
        """
        # Test reading with default behavior
        recipe = f"""  
        read:  
            - xlsb:  
                name: tests/samples/data3.xlsb  
                sheet_name: MixedTypes
                columns:  
                    - mixed_with_na
                keep_default_na: false
        """
        df = wrangles.recipe.run(recipe)

        # Verify dtype is object
        assert df["mixed_with_na"].dtype == "object"

        # Check values are preserved (empty strings become empty strings due to fillna(""))
        assert df["mixed_with_na"].iloc[0] == "text"
        assert df["mixed_with_na"].iloc[1] == 123
        assert df["mixed_with_na"].iloc[2] == ""
        assert df["mixed_with_na"].iloc[3] == ""
        assert df["mixed_with_na"].iloc[4] == "NA"
        assert df["mixed_with_na"].iloc[5] == "N/A"
        assert df["mixed_with_na"].iloc[6] == 456.78

        # Test with custom na_values
        recipe_na = f"""  
        read:  
         - xlsb:  
            name: tests/samples/data3.xlsb  
            sheet_name: MixedTypes
            columns:  
                - mixed_with_na
            na_values:  
                - NA  
                - N/A  
            keep_default_na: false  
        """
        df_na = wrangles.recipe.run(recipe_na)

        # Check that custom NA values are converted to empty string (due to fillna)
        assert df_na["mixed_with_na"].iloc[4] == ""
        assert df_na["mixed_with_na"].iloc[5] == ""

    def test_read_xlsb_datetime_various_formats(self):
        """
        Test reading XLSB with date/datetime columns in various formats
        """
        # Test reading with parse_dates=True (default behavior)
        recipe = f"""  
        read:  
        - xlsb:  
            name: tests/samples/data3.xlsb  
            sheet_name: Dates  
            parse_dates: true  
        """
        df = wrangles.recipe.run(recipe)

        # Check that parse_dates attempts conversion but preserves as object due to mixed formats
        assert df["date_us"].dtype == "object"
        assert df["date_iso"].dtype == "object"

        # Test reading with column-specific parse_dates
        recipe_specific = f"""  
        read:  
        - xlsb:  
            name: tests/samples/data3.xlsb
            sheet_name: Dates 
            parse_dates:  
                - date_iso  
                - datetime_full  
        """
        df_specific = wrangles.recipe.run(recipe_specific)

        # Only specified columns should be datetime
        assert _pd.api.types.is_datetime64_any_dtype(df_specific["date_iso"])
        assert _pd.api.types.is_datetime64_any_dtype(df_specific["datetime_full"])
        assert df_specific["date_us"].dtype == "object"  # Not parsed

    def test_read_xlsb_numeric_precision(self):
        """
        Test reading XLSB with various numeric precisions
        """
        # Test reading with default dtype (object)
        recipe = f"""  
        read:  
        - xlsb:  
            name: tests/samples/data3.xlsb
            sheet_name: Numeric 
        """
        df = wrangles.recipe.run(recipe)

        # Verify precision is preserved with object dtype
        assert df["float64_values"].iloc[0] == 3.141592653589793
        assert df["high_precision"].iloc[0] == 1.23456789012345
        assert df["very_small"].iloc[0] == 1e-10
        assert df["very_large"].iloc[0] == 1e10

        # Test reading with float32 dtype
        recipe_float32 = f"""  
        read:  
        - xlsb:  
            name: tests/samples/data3.xlsb
            sheet_name: Numeric
            dtype:  
                float64_values: float32  
                high_precision: float32  
        """
        df_float32 = wrangles.recipe.run(recipe_float32)

        # Check precision reduction to float32
        assert df_float32["float64_values"].dtype == "float32"

    def test_read_xlsb_boolean_values(self):
        """
        Test reading XLSB with various boolean representations
        """
        # Test reading with default behavior (object dtype)
        recipe = f"""  
        read:  
          - xlsb:  
                name: tests/samples/data3.xlsb
                sheet_name: Booleans
        """
        df = wrangles.recipe.run(recipe)

        # Verify boolean types are preserved as object dtype
        # assert df['bool_standard'].dtype == 'object'
        # assert df['mixed_bool'].dtype == 'object'

        # Check specific values are preserved
        assert df["bool_standard"].iloc[0] == True
        assert df["bool_numeric"].iloc[0] == 1
        assert df["bool_text"].iloc[0] == "True"
        assert df["bool_yes_no"].iloc[0] == "Yes"

    def test_read_xlsb_boolean_with_true_false_values(self):
        """
        Test reading XLSB with custom true_values and false_values parameters
        """
        # Test reading with custom true/false values
        recipe = f"""  
        read:  
            - xlsb:  
                name: tests/samples/data3.xlsb
                sheet_name: CustomBools
                true_values: [True, 1, 'Yes', 'Y', 'true', 'True']  
                false_values: [False, 0, 'No', 'N', 'false', 'False']  
                dtype:  
                    custom_bool: bool  
        """
        df = wrangles.recipe.run(recipe)

        # Verify conversion to boolean
        assert df["custom_bool"].dtype == "bool"
        assert df["custom_bool"].iloc[0] == True  # Yes
        assert df["custom_bool"].iloc[1] == False  # No
        assert df["custom_bool"].iloc[2] == True  # Y
        assert df["custom_bool"].iloc[3] == False  # N
        assert df["custom_bool"].iloc[4] == True  # TRUE
        assert df["custom_bool"].iloc[5] == False  # FALSE
        assert df["custom_bool"].iloc[6] == True  # 1
        assert df["custom_bool"].iloc[7] == False  # 0

    def test_read_xlsb_empty_null_string_distinctions(self):
        """
        Test reading XLSB with empty cells, NULL values, and "NULL" strings
        """
        # Test reading with default behavior
        recipe = f"""  
        read:  
            - xlsb:  
                name: tests/samples/data3.xlsb
                sheet_name: NullValues 
        """
        df = wrangles.recipe.run(recipe)

        # With default fillna(""), all NULL/NaN become empty strings
        # But "NULL" strings remain as "NULL"
        assert df["empty_cells"].iloc[0] == ""  # Empty stays empty
        assert df["null_values"].iloc[0] == ""  # NULL becomes empty string
        assert df["mixed_nulls"].iloc[0] == ""  # Empty stays empty
        assert df["mixed_nulls"].iloc[1] == ""  # None becomes empty string
        assert df["mixed_nulls"].iloc[3] == ""  # NaN becomes empty string

        # Test with custom na_values to treat "NULL" string as NULL
        recipe_custom = f"""  
        read:  
            - xlsb:  
                name: tests/samples/data3.xlsb
                sheet_name: NullValues
                na_values: ['NULL', 'null', 'Null'] 
                keep_default_na: true  
        """
        df_custom = wrangles.recipe.run(recipe_custom)

        # Now "NULL" strings should also become empty strings due to fillna
        assert df_custom["null_strings"].iloc[0] == ""  # "NULL" becomes empty
        assert df_custom["null_strings"].iloc[1] == ""  # "null" becomes empty
        assert df_custom["null_strings"].iloc[2] == ""  # "Null" becomes empty
        assert df_custom["null_strings"].iloc[3] == ""  # "NULL" becomes empty

    def test_read_xlsb_large_numbers(self):
        """
        Test reading XLSB with large numbers beyond int32 range
        """
        # Test reading with default dtype (object)
        recipe = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: LargeNumbers 
        """
        df = wrangles.recipe.run(recipe)

        # Verify large numbers are preserved with object dtype
        # assert df['beyond_int32_positive'].dtype == 'object'
        assert df["beyond_int32_positive"].iloc[0] == 2147483648
        assert df["beyond_int32_positive"].iloc[1] == 4294967295
        assert df["beyond_int32_positive"].iloc[2] == 9223372036854775808

        assert df["beyond_int32_negative"].iloc[0] == -2147483649
        assert df["beyond_int32_negative"].iloc[1] == -4294967296

        # Test reading with int64 dtype
        recipe_int64 = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: LargeNumbers 
              dtype:  
                beyond_int32_positive: int64  
                beyond_int32_negative: int64  
                very_large_integers: int64  
        """
        df_int64 = wrangles.recipe.run(recipe_int64)

        # Check conversion to int64
        assert df_int64["beyond_int32_positive"].dtype == "int64"
        assert df_int64["beyond_int32_positive"].iloc[0] == 2147483648
        assert df_int64["beyond_int32_negative"].dtype == "int64"
        assert df_int64["beyond_int32_negative"].iloc[0] == -2147483649

        # Test reading with float64 for very large numbers
        recipe_float = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: LargeNumbers
              dtype:  
                very_large_integers: float64  
                large_floats: float64  
        """
        df_float = wrangles.recipe.run(recipe_float)

        # Check that very large integers might lose precision as float64
        assert df_float["very_large_integers"].dtype == "float64"
        # Float64 has about 15-17 significant digits
        # assert df_float['very_large_integers'].iloc[0] == 1234567890123456789.0

    def test_read_xlsb_nrows_skipfooter_interaction(self):
        """
        Test nrows and skipfooter parameter interaction
        """
        with pytest.raises(
            ValueError, match="skipfooter cannot be used together with nrows"
        ):
            wrangles.recipe.run(
                """  
            read:  
              - xlsb:  
                  name: tests/samples/data3.xlsb
                  sheet_name: NrowFooter
                  nrows: 5  
                  skipfooter: 2  
            """,
            )

    def test_read_xlsb_skiprows_header_interaction(self):
        """
        Test the interaction between skiprows and header parameters
        """
        # Test 1: skiprows=2, header=0 (header at original row 0)
        recipe1 = f"""  
        read:  
            - xlsb:  
                name: tests/samples/data3.xlsb
                sheet_name: SkiprowHeader
                skiprows: 3  
                header: 0  
        """
        df1 = wrangles.recipe.run(recipe1)
        # With pandas behavior: skip rows 0-2, then use row 0 as header (which is now original row 3)

        assert df1.columns.tolist() == ["header_col1", "header_col2", "header_col3"]
        assert len(df1) == 3  # Rows 3-5 become data

        # Test 2: skiprows=2, header=2 (header at original row 2)
        recipe2 = f"""  
        read:  
            - xlsb:  
                name: tests/samples/data3.xlsb
                sheet_name: SkiprowHeader
                skiprows: 3  
                header: 2  
        """
        df2 = wrangles.recipe.run(recipe2)
        # Skip rows 0-2, then use row 2 as header (original row 5)
        assert df2.columns.tolist() == ["data_row2_1", "data_row2_2", "data_row2_3"]
        assert len(df2) == 1  # Only rows 5+ remain as data

        # Test 3: skiprows=2, header=None
        recipe3 = f"""  
        read:  
            - xlsb:  
                name: tests/samples/data3.xlsb
                sheet_name: SkiprowHeader
                skiprows: 3  
                header: null  
        """
        df3 = wrangles.recipe.run(recipe3)
        # Skip rows 0-1, no header, all remaining rows are data
        assert df3.columns.tolist() == [0, 1, 2]
        assert len(df3) == 4
        assert df3.iloc[0, 0] == "header_col1"  # First data row is original row 2

        # Test 4: skiprows as list
        recipe4 = f"""  
        read:  
            - xlsb:  
                name: tests/samples/data3.xlsb
                sheet_name: SkiprowHeader
                skiprows: [1, 3, 4]  
                header: 0  
        """
        df4 = wrangles.recipe.run(recipe4)

        assert df4.iloc[0, 0] == "should_be_skipped_2"
        assert df4.iloc[1, 0] == "data_row2_1"
        assert df4.iloc[2, 0] == "data_row3_1"

    def test_read_xlsb_names_wrong_column_count(self):
        """
        Test reading XLSB with names parameter having wrong number of columns
        """

        # Test 1: Too few names (1 names for 2 columns) merge columns
        recipe = f"""  
            read:  
              - xlsb:  
                  name: tests/samples/data3.xlsb
                  sheet_name: Basic  
                  names:  
                    - CustomName1  
            """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ["CustomName1"]

        # Test 2: Too many names (4 names for 2 columns)
        with pytest.raises(
            ValueError,
            match="Number of passed names did not match number of header fields",
        ):
            recipe = f"""  
            read:  
              - xlsb:  
                  name: tests/samples/data3.xlsb
                  sheet_name: Basic
                  header: 0  
                  names:  
                    - CustomName1  
                    - CustomName2  
                    - CustomName3  
                    - CustomName4  
            """
            wrangles.recipe.run(recipe)

        # Test 3: Correct number of names (should work)
        recipe = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: Basic
              header: 0  
              names:  
                - CustomName1  
                - CustomName2  
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ["CustomName1", "CustomName2"]

    def test_read_xlsb_names_with_header_none(self):
        """
        Test reading XLSB with names parameter and header=None
        """
        # Test with correct number of names and header=None
        recipe = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: NoHeaders
              header: null  
              names:  
                - CustomCol1  
                - CustomCol2  
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ["CustomCol1", "CustomCol2"]
        assert len(df) == 2

    def test_read_xlsb_converters_with_functions(self):
        """
        Test reading XLSB with converters using custom functions
        """

        # Test with a valid converter function
        def uppercase_converter(x):
            return str(x).upper() if _pd.notna(x) else x

        df = wrangles.connectors.xlsb.read(
            "tests/samples/data3.xlsb",
            sheet_name="ConverterFormula",
            converters={"text": uppercase_converter},
        )
        assert df["text"].iloc[0] == "ABC"

    def test_read_xlsb_index_col_multi_index(self):
        """
        Test reading XLSB with index_col parameter creating multi-index
        """

        # Test 1: Create multi-index with two columns
        recipe1 = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: MultiIndex
              index_col: [0, 1]
        """
        df1 = wrangles.recipe.run(recipe1)

        # Verify multi-index is created
        assert isinstance(df1.index, _pd.MultiIndex)
        assert df1.index.nlevels == 2
        assert list(df1.index.names) == ["Region", "Category"]
        # Check that data columns exclude index columns
        assert df1.columns.tolist() == ["Product", "Sales", "Quantity"]
        assert len(df1) == 6

        # Test 2: Create multi-index with three columns
        recipe2 = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: MultiIndex 
              index_col: [0, 1, 2]
        """
        df2 = wrangles.recipe.run(recipe2)

        # Verify three-level multi-index
        assert isinstance(df2.index, _pd.MultiIndex)
        assert df2.index.nlevels == 3
        assert list(df2.index.names) == ["Region", "Category", "Product"]
        assert df2.columns.tolist() == ["Sales", "Quantity"]

        # Test 3: Single column index (not multi-index)
        recipe3 = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: MultiIndex 
              index_col: Region
        """
        df3 = wrangles.recipe.run(recipe3)

        # Verify single index (not MultiIndex)
        assert not isinstance(df3.index, _pd.MultiIndex)
        assert df3.index.name == "Region"
        assert df3.columns.tolist() == ["Category", "Product", "Sales", "Quantity"]

    def test_read_xlsb_index_col_multi_index_with_column_selection(self):
        """
        Test reading XLSB with multi-index and column selection
        """
        # Test multi-index with column selection
        recipe = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: MultiIndex 
              index_col:  [0, 1]
              columns:  
                - Sales  
                - Quantity  
        """
        df = wrangles.recipe.run(recipe)

        # Verify multi-index and selected columns
        assert isinstance(df.index, _pd.MultiIndex)
        assert df.index.nlevels == 2
        assert df.columns.tolist() == ["Sales", "Quantity"]
        # Product and Price should not be included

    def test_read_xlsb_wildcard_patterns(self):
        """
        Test XLSB connector with various wildcard/regex column patterns
        """

        # Test wildcard pattern
        recipe = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: Wildcards
              columns:  
                - Col*  
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ["Col1", "Col2"]

        # Test regex pattern
        recipe = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: Wildcards 
              columns:  
                - regex:Col[1-2]  
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ["Col1", "Col2"]

        # Test negative pattern
        recipe = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: Wildcards
              columns:  
                - "*"  
                - -Ignore*  
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ["Col1", "Col2", "Different"]

        # Test optional pattern
        recipe = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: Wildcards 
              columns:  
                - Col1  
                - NonExistentCol?  
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ["Col1"]

    def test_read_xlsb_different_path_types(self):
        """
        Test reading XLSB files with different path types (relative, absolute)
        """

        recipe = f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb
              sheet_name: Basic
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ["Find", "Replace"]
        assert len(df) == 3

        # Test 2: Absolute path
        absolute_path = os.path.abspath("tests/samples/data3.xlsb")
        print(absolute_path)
        recipe = f"""  
        read:  
          - xlsb:  
              name: {absolute_path}  
              sheet_name: Basic
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ["Find", "Replace"]
        assert len(df) == 3
