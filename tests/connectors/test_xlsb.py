import wrangles
import pytest
import pandas as _pd

class TestXLSBConnector:
    def test_read_xlsb_basic_functionality(self):
        """
        Test basic .xlsb import with common parameters
        """

        # Test basic read with columns and nrows
        recipe = """  
          read:  
            - xlsb:  
                name: tests/samples/data.xlsb  
                columns:  
                  - Find  
                nrows: 3  
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ["Find"]
        assert len(df) <= 3

    def test_read_xlsb_sheet_and_header_options(self):
        """
        Test sheet selection and header parameters together
        """

        # Test sheet name and header together
        recipe = """  
          read:  
            - xlsb:  
                name: tests/samples/data.xlsb  
                sheet_name: 0  
                header: 0  
                skiprows: 0  
        """
        df = wrangles.recipe.run(recipe)
        assert len(df) > 0
        assert df.columns.tolist() == ["Find", "Replace"]

    def test_read_xlsb_column_selection_options(self):
        """
        Test various column selection methods
        """
        # Test usecols vs columns parameter
        recipe = """  
          read:  
            - xlsb:  
                name: tests/samples/data.xlsb  
                usecols:  
                  - Find  
                dtype: object  
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ["Find"]
        assert df.dtypes.apply(str).unique()[0] == "object"

    def test_read_xlsb_data_formatting_options(self):
        """
        Test data formatting and NA handling parameters
        """

        # Test multiple formatting options together
        recipe = """  
          read:  
            - xlsb:  
                name: tests/samples/data.xlsb  
                na_values:  
                  - N/A  
                  - NULL  
                keep_default_na: true  
                na_filter: true  
                decimal: '.'  
                thousands: ','  
                verbose: false  
        """
        df = wrangles.recipe.run(recipe)
        assert len(df) > 0
        assert df.columns.tolist() == ["Find", "Replace"]

    def test_read_xlsb_advanced_parameters(self):
        """
        Test advanced parameters like date parsing and file operations
        """
        # Test advanced options
        recipe = """  
          read:  
            - xlsb:  
                name: tests/samples/data.xlsb  
                parse_dates: false  
                skipfooter: 0  
                comment: null  
        """
        df = wrangles.recipe.run(recipe)
        assert len(df) > 0

class TestXLSBConnectorErrorHandling:  
    """  
    Test error handling scenarios for xlsb connector  
    """  
      
    def test_file_not_found(self):  
        """  
        Test FileNotFoundError when file doesn't exist  
        """  
        with pytest.raises(FileNotFoundError, match="File not found"):  
            wrangles.recipe.run("""  
            read:  
              - xlsb:  
                  name: tests/samples/non_existent_file.xlsb
            """)   
      
    def test_invalid_sheet_name(self):  
        """  
        Test error with invalid sheet name  
        """   
          
        with pytest.raises(ValueError, match="xlsb - Invalid sheet name or index: NonExistentSheet"):  
            wrangles.recipe.run(f"""  
            read:  
              - xlsb:  
                  name: tests/samples/data.xlsb  
                  sheet_name: NonExistentSheet  
            """)  
      
    def test_invalid_sheet_index(self):  
        """  
        Test error with invalid sheet index  
        """  
        with pytest.raises(ValueError, match="Invalid sheet name or index: 5"):  
            wrangles.recipe.run(f"""  
            read:  
              - xlsb:  
                  name: tests/samples/data.xlsb  
                  sheet_name: 5  
            """)  
      
    def test_non_existent_columns(self):  
        """  
        Test error when requesting non-existent columns with context  
        """  
        with pytest.raises(KeyError) as exc_info:  
            wrangles.recipe.run(f"""  
            read:  
              - xlsb:  
                  name: tests/samples/data.xlsb  
                  columns:  
                    - NonExistentColumn  
            """)  
        assert "Available columns: [\\\'Find\\\', \\\'Replace\\\']" in str(exc_info.value)  
      
    def test_empty_file(self):  
        """  
        Test reading empty file (0 rows, 0 columns)  
        """  
        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/empty.xlsb   
        """)  
        assert len(df) == 0  
        assert len(df.columns) == 0  
      
    def test_no_headers(self):  
        """  
        Test reading file with no headers (header=None)  
        """  

        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: NoHeaders
              header: null  
        """)  
        assert df.columns.tolist() == [0, 1]  
        assert len(df) == 2
      
    def test_no_headers_with_names(self):  
        """  
        Test reading file with no headers but providing custom names  
        """  

        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data.xlsb 
              header: null  
              names:  
                - CustomCol1  
                - CustomCol2  
        """)  
        assert df.columns.tolist() == ['CustomCol1', 'CustomCol2']  
        assert len(df) == 4
      
    def test_wrong_file_extension(self):  
        """  
        Test that file without .xlsb extension raises appropriate error  
        """  
        
        with pytest.raises(ValueError, match="File must have .xlsb extension"):  
            wrangles.recipe.run(f"""  
            read:  
              - xlsb:  
                  name: tests/samples/data.txt  
            """)  
      
    def test_sheet_list_with_invalid_sheet(self):  
        """  
        Test error when list contains non-existent sheet  
        """  
        with pytest.raises(ValueError, match="Invalid sheet name or index"):  
            wrangles.recipe.run(f"""  
            read:  
              - xlsb:  
                  name: tests/samples/data.xlsb  
                  sheet_name:  
                    - Sheet1  
                    - NonExistent  
            """)

class TestXLSBConnectorEdgeCases:  
    """  
    Test edge case scenarios for xlsb connector  
    """   
      
    def test_multiple_sheets_list(self):  
        """  
        Test reading specific sheets as list  
        """  
        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data2.xlsb 
              sheet_name: [0, 1]  
        """)  
        assert isinstance(df, _pd.DataFrame)  
        assert len(df) == 2  
      
    def test_special_characters_columns(self):  
        """  
        Test file with special characters in column names  
        """  

        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: SpecialChars
        """)  
        assert 'Col!@#' in df.columns  
      
    def test_duplicate_columns(self):  
        """  
        Test file with duplicate column names  
        """  
        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data2.xlsb 
              sheet_name: Sheet4 
        """)  
        assert len(df.columns) == 2  
      
    def test_only_headers(self):  
        """  
        Test file with only headers (0 data rows)  
        """  
        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: HeadersOnly
        """)  
        assert len(df) == 0  
        assert df.columns.tolist() == ['Col1', 'Col2', 'Col3']  
      
    def test_formulas_and_calculated_values(self):  
        """  
        Test file with formulas and calculated values  
        """  
        # Read and verify formulas are evaluated as values  
        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data2.xlsb 
              sheet_name: Sheet6       
        """)  
        assert len(df) == 3  

class TestDataTypes:  
    """  
    Test data type handling for xlsb connector  
    """  
      
    def test_mixed_data_types(self):  
      """  
      Test mixed data types in columns  
      """  
      df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: MixedTypes
        """
      )  
      assert len(df) == 6  
      assert df.iloc[0, 0] == 'text'  
      assert df.iloc[5, 0] in ['more text']  
      
    def test_datetime_columns_various_formats(self):  
        """  
        Test date/datetime columns with various formats  
        """  
        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: Dates
              parse_dates: true  
        """)  
        assert len(df) == 3  
        # Verify dates are preserved (may remain as strings without explicit format)  
        assert '12/25/2023' in str(df.iloc[0, 0])  
      
    def test_numeric_precision_floats_decimals(self):  
        """  
        Test numeric precision (floats, decimals)  
        """  

        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: Numeric
        """)  
        assert len(df) == 3 
        # Check precision is maintained  
        assert abs(df.iloc[0, 0] - 1.23456789) < 0.00000001  
        assert abs(df.iloc[1, 1] - 678.90) < 0.01  
      
    def test_boolean_values_various_formats(self):  
        """  
        Test various boolean representations  
        """  
        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: Booleans
              true_values: [True, 1, 'Yes', 'Y', 'true', 'True']  
              false_values: [False, 0, 'No', 'N', 'false', 'False']  
        """)  
        assert len(df) == 3  
        # Verify boolean values are preserved  
        assert df.iloc[0, 0] == True  
        assert df.iloc[1, 0] == False  
      
    def test_empty_cells_vs_null_vs_string(self):  
        """  
        Test empty cells vs NULL vs "NULL" string  
        """  

        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: NullValues
        """)  
        assert len(df) == 5
        # Check handling of different null representations  
        assert df.iloc[0, 0] == ''  # Empty string preserved  
        assert df.iloc[1, 0] == ''  # None converted to empty string by fillna  
        assert df.iloc[2, 0] == ''  # String "NULL" preserved  
      
    def test_large_numbers_beyond_int32(self):  
        """  
        Test large numbers beyond int32 range  
        """  
        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: LargeNumbers
        """)  
        assert len(df) == 3
        # Verify large numbers are handled correctly  
        assert df.iloc[0, 0] == 2147483648  # Beyond int32 max (2147483647)  
        assert df.iloc[0, 1] == 1234567890123450 
      
    def test_unicode_special_characters(self):  
        """  
        Test unicode and special characters  
        """  
        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data2.xlsb 
              sheet_name: Sheet13
        """)  
        assert len(df) == 5 
        # Verify unicode characters are preserved  
        assert df.iloc[0, 0] == 'café'  
        assert df.iloc[1, 0] == 'naïve'  
        assert df.iloc[4, 0] == '🚀'  
      
    def test_mixed_numeric_types(self):  
        """  
        Test mixed numeric types in same column  
        """  
        df = wrangles.recipe.run(f"""  
        read:  
          - xlsb:  
              name: tests/samples/data3.xlsb 
              sheet_name: Parameters
        """)  
        assert len(df) == 5 
        assert df.iloc[1, 0] == 'b' 
        assert df.iloc[2, 1] == 3 
        assert df.iloc[3, 2] == 6

    def test_columns_usecols_mutually_exclusive(self):  
        """  
        Test that columns and usecols parameters are mutually exclusive  
        """  
        with pytest.raises(KeyError, match=r"Column A does not exist"):  
            wrangles.recipe.run(  
                """  
                read:  
                  - xlsb:  
                      name: tests/samples/data2.xlsb 
                      sheet_name: Sheet2
                      columns:  
                        - A  
                      usecols:  
                        - B  
                """
            ) 
    def test_usecols_parameter_only(self):  
        """  
        Test usecols parameter works without columns  
        """  
        df = wrangles.recipe.run(  
            """  
            read:  
              - xlsb:  
                  name: tests/samples/data2.xlsb 
                  sheet_name: Sheet6
                  usecols: "A:B"
              """
        )  
        assert len(df.columns) == 2  

    def test_nrows_skipfooter_interaction(self):  
        """  
        Test nrows and skipfooter parameter interaction  
        """  
        df = wrangles.recipe.run(  
            """  
            read:  
              - xlsb:  
                  name: tests/samples/data3.xlsb
                  sheet_name: NrowFooter
                  nrows: 5  
                  skipfooter: 2  
            """,  
        )  
        assert len(df) == 3  # 5 rows - 2 footer rows  

    # def test_converters_invalid_column_name(self):  
    #     """  
    #     Test converters parameter with invalid column name raises error  
    #     """  

    #     # with pytest.raises(KeyError, match="NonExistentColumn"):  
    #     df = wrangles.recipe.run(  
    #             """  
    #             read:  
    #               - xlsb:  
    #                   name: tests/samples/data3.xlsb
    #                   sheet_name: Parameters
    #                   converters:  
    #                     NonExistentColumn: str  
    #             """,  
    #         ) 
    #     print(df)
    #     assert False

    def test_converters_valid_column_name(self):  
        """  
        Test converters parameter with valid column name raises error  
        """  
        df = wrangles.recipe.run(  
                """  
                read:  
                  - xlsb:  
                    name: tests/samples/data2.xlsb 
                    sheet_name: Sheet6
                    converters:  
                      A: str  
                """,  
            ) 
        assert df.iloc[1, 1] == '4'  # Converted to string