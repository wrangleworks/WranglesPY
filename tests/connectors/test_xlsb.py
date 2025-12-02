import wrangles

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
