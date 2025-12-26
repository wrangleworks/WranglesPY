"""
Test the json connector for reading and writing JSON and JSONL files.

This connector provides explicit parameter handling to avoid issues
with incompatible arguments being passed to pandas read_json/to_json.
"""
import uuid as _uuid
import json as _json
import os as _os

import pandas as _pd
import pytest

import wrangles


class TestRead:
    """
    Test reading JSON and JSONL files with the json connector
    """
    
    def test_read_json_basic(self):
        """
        Test a basic .json import using the json connector
        """
        recipe = """
          read:
            - json:
                name: tests/samples/data.json
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_read_jsonl_basic(self):
        """
        Test a basic .jsonl import using the json connector
        """
        recipe = """
          read:
            - json:
                name: tests/samples/data.jsonl
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_read_json_with_columns(self):
        """
        Test reading JSON with column selection
        """
        recipe = """
          read:
            - json:
                name: tests/samples/data.json
                columns:
                  - Find
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find']

    def test_read_jsonl_with_columns(self):
        """
        Test reading JSONL with column selection
        """
        recipe = """
          read:
            - json:
                name: tests/samples/data.jsonl
                columns:
                  - Find
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find']

    def test_read_json_with_orient(self):
        """
        Test reading JSON with explicit orient parameter
        """
        recipe = """
          read:
            - json:
                name: tests/samples/data.json
                orient: records
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_read_jsonl_with_nrows(self):
        """
        Test reading JSONL with nrows parameter.
        This should work because JSONL uses lines=True.
        """
        recipe = """
          read:
            - json:
                name: tests/samples/data.jsonl
                nrows: 2
        """
        df = wrangles.recipe.run(recipe)
        assert len(df) == 2

    def test_read_json_with_nrows_error(self):
        """
        Test that reading JSON (not JSONL) with nrows raises an error.
        This is the key issue this connector solves - preventing invalid parameter combinations.
        """
        with pytest.raises(ValueError, match="nrows.*only supported.*JSONL"):
            recipe = """
              read:
                - json:
                    name: tests/samples/data.json
                    nrows: 2
            """
            wrangles.recipe.run(recipe)

    def test_read_json_with_encoding(self):
        """
        Test reading JSON with explicit encoding
        """
        recipe = """
          read:
            - json:
                name: tests/samples/data.json
                encoding: utf-8
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_read_jsonl_explicit_lines(self):
        """
        Test reading with explicit lines=True parameter
        """
        recipe = """
          read:
            - json:
                name: tests/samples/data.jsonl
                lines: true
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_read_json_direct_call(self):
        """
        Test reading JSON using direct connector call
        """
        df = wrangles.connectors.json.read('tests/samples/data.json')
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_read_jsonl_direct_call(self):
        """
        Test reading JSONL using direct connector call
        """
        df = wrangles.connectors.json.read('tests/samples/data.jsonl')
        assert df.columns.tolist() == ['Find', 'Replace']

    def test_read_jsonl_with_nrows_direct(self):
        """
        Test reading JSONL with nrows using direct call
        """
        df = wrangles.connectors.json.read('tests/samples/data.jsonl', nrows=2)
        assert len(df) == 2

    def test_read_json_with_nrows_direct_error(self):
        """
        Test that direct call with nrows on regular JSON raises helpful error
        """
        with pytest.raises(ValueError, match="nrows.*only supported.*JSONL"):
            wrangles.connectors.json.read('tests/samples/data.json', nrows=2)

    def test_read_multiple_json_sources(self):
        """
        Test reading multiple JSON sources in a single read section.
        This demonstrates the list format enables multiple connector invocations
        which are automatically combined via union.
        """
        recipe = """
          read:
            - json:
                name: tests/samples/data.json
                columns:
                  - Find
            - json:
                name: tests/samples/data.jsonl
                columns:
                  - Replace
        """
        df = wrangles.recipe.run(recipe)
        assert 'Find' in df.columns and 'Replace' in df.columns
        assert len(df) == 6

class TestWrite:
    """
    Test writing JSON and JSONL files with the json connector
    """
    
    def test_write_json_basic(self):
        """
        Test writing a basic .json file
        """
        filename = f"tests/temp/{_uuid.uuid4()}.json"
        recipe = f"""
          read:
            - test:
                rows: 5
                values:
                  Find: aaa
                  Replace: bbb
          write:
            - json:
                name: {filename}
        """
        wrangles.recipe.run(recipe)
        
        df = wrangles.connectors.json.read(filename)
        assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 5
        
        _os.remove(filename)

    def test_write_jsonl_basic(self):
        """
        Test writing a basic .jsonl file
        """
        filename = f"tests/temp/{_uuid.uuid4()}.jsonl"
        recipe = f"""
          read:
            - test:
                rows: 5
                values:
                  Find: aaa
                  Replace: bbb
          write:
            - json:
                name: {filename}
        """
        wrangles.recipe.run(recipe)
        
        df = wrangles.connectors.json.read(filename)
        assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 5
        
        _os.remove(filename)

    def test_write_json_with_columns(self):
        """
        Test writing JSON with column selection
        """
        filename = f"tests/temp/{_uuid.uuid4()}.json"
        recipe = f"""
          read:
            - test:
                rows: 5
                values:
                  Find: aaa
                  Replace: bbb
                  Extra: ccc
          write:
            - json:
                name: {filename}
                columns:
                  - Find
                  - Replace
        """
        wrangles.recipe.run(recipe)
        
        df = wrangles.connectors.json.read(filename)
        assert df.columns.tolist() == ['Find', 'Replace'] and len(df) == 5
        
        _os.remove(filename)

    def test_write_json_with_orient(self):
        """
        Test writing JSON with explicit orient parameter
        """
        filename = f"tests/temp/{_uuid.uuid4()}.json"
        recipe = f"""
          read:
            - test:
                rows: 3
                values:
                  col1: val1
                  col2: val2
          write:
            - json:
                name: {filename}
                orient: records
        """
        wrangles.recipe.run(recipe)

        with open(filename, 'r') as f:
            data = _json.load(f)
        assert isinstance(data, list) and len(data) == 3
        
        _os.remove(filename)

    def test_write_json_with_indent(self):
        """
        Test writing JSON with indentation for pretty-printing
        """
        filename = f"tests/temp/{_uuid.uuid4()}.json"
        recipe = f"""
          read:
            - test:
                rows: 2
                values:
                  col1: val1
          write:
            - json:
                name: {filename}
                indent: 2
        """
        wrangles.recipe.run(recipe)
        
        with open(filename, 'r') as f:
            content = f.read()
        assert '  ' in content
        
        # Cleanup
        _os.remove(filename)

    def test_write_jsonl_indent_warning(self):
        """
        Test that indent parameter with JSONL shows warning but doesn't fail
        """
        filename = f"tests/temp/{_uuid.uuid4()}.jsonl"
        df = _pd.DataFrame({'col1': ['val1', 'val2']})
        
        wrangles.connectors.json.write(df, filename, indent=2)
        
        assert _os.path.exists(filename)
        
        _os.remove(filename)

    def test_write_json_direct_call(self):
        """
        Test writing JSON using direct connector call
        """
        filename = f"tests/temp/{_uuid.uuid4()}.json"
        df = _pd.DataFrame({
            'col1': ['a', 'b', 'c'],
            'col2': [1, 2, 3]
        })
        
        wrangles.connectors.json.write(df, filename)
        
        result_df = wrangles.connectors.json.read(filename)
        assert result_df.columns.tolist() == ['col1', 'col2'] and len(result_df) == 3
        
        _os.remove(filename)

    def test_write_jsonl_direct_call(self):
        """
        Test writing JSONL using direct connector call
        """
        filename = f"tests/temp/{_uuid.uuid4()}.jsonl"
        df = _pd.DataFrame({
            'col1': ['a', 'b', 'c'],
            'col2': [1, 2, 3]
        })
        
        wrangles.connectors.json.write(df, filename)
        
        result_df = wrangles.connectors.json.read(filename)
        assert result_df.columns.tolist() == ['col1', 'col2'] and len(result_df) == 3
        
        _os.remove(filename)

    def test_write_json_create_directory(self):
        """
        Test that writing JSON creates directory if it doesn't exist
        """
        test_dir = f"tests/temp/{_uuid.uuid4()}"
        filename = f"{test_dir}/test.json"
        
        df = _pd.DataFrame({'col1': ['val1']})
        wrangles.connectors.json.write(df, filename)
        
        assert _os.path.exists(filename)
        
        _os.remove(filename)
        _os.rmdir(test_dir)

    def test_write_json_with_compression(self):
        """
        Test writing compressed JSON file
        """
        filename = f"tests/temp/{_uuid.uuid4()}.json.gz"
        df = _pd.DataFrame({
            'col1': ['a', 'b', 'c'],
            'col2': [1, 2, 3]
        })
        
        wrangles.connectors.json.write(df, filename)
        
        result_df = wrangles.connectors.json.read(filename)
        assert len(result_df) == 3
        
        _os.remove(filename)

    def test_write_jsonl_with_compression(self):
        """
        Test writing compressed JSONL file
        """
        filename = f"tests/temp/{_uuid.uuid4()}.jsonl.gz"
        df = _pd.DataFrame({
            'col1': ['a', 'b', 'c'],
            'col2': [1, 2, 3]
        })
        
        wrangles.connectors.json.write(df, filename)
        
        result_df = wrangles.connectors.json.read(filename)
        assert len(result_df) == 3

        _os.remove(filename)


class TestParameterValidation:
    """
    Test parameter validation and error handling
    """
    
    def test_nrows_with_regular_json_error_message(self):
        """
        Test that the error message for nrows with regular JSON is helpful
        """
        try:
            wrangles.connectors.json.read('tests/samples/data.json', nrows=5)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            error_msg = str(e)
            assert 'nrows' in error_msg
            assert 'JSONL' in error_msg or 'lines=True' in error_msg
            assert 'only supported' in error_msg

    def test_auto_detect_jsonl_format(self):
        """
        Test that JSONL format is auto-detected from .jsonl extension
        """
        # This should work because .jsonl auto-sets lines=True
        df = wrangles.connectors.json.read('tests/samples/data.jsonl', nrows=2)
        assert len(df) == 2

    def test_auto_detect_json_format(self):
        """
        Test that regular JSON format is auto-detected from .json extension
        """
        # This should work for regular JSON without nrows
        df = wrangles.connectors.json.read('tests/samples/data.json')
        assert len(df) > 0

    def test_explicit_lines_parameter(self):
        """
        Test that explicit lines=True parameter enables nrows
        """
        # Force lines=True for a .json file (unusual but should work if data is line-delimited)
        df = wrangles.connectors.json.read('tests/samples/data.jsonl', lines=True, nrows=2)
        assert len(df) == 2


class TestChunksize:
    def test_read_jsonl_with_chunksize(self):
        """
        Test reading JSONL with chunksize
        """
        reader = wrangles.connectors.json.read('tests/samples/data.jsonl', chunksize=2)
        
        chunks = list(reader)
        assert len(chunks) > 0
        
        for chunk in chunks:
            assert isinstance(chunk, _pd.DataFrame)
            assert 'Find' in chunk.columns and 'Replace' in chunk.columns
            assert chunk.isnull().sum().sum() == 0
    
    def test_read_jsonl_with_chunksize_and_columns(self):
        """
        Test reading JSONL with chunksize and column selection
        """
        reader = wrangles.connectors.json.read('tests/samples/data.jsonl', chunksize=2, columns=['Find'])
        
        chunks = list(reader)
        assert len(chunks) > 0
        
        for chunk in chunks:
            assert chunk.columns.tolist() == ['Find']
    
    def test_read_jsonl_with_chunksize_direct(self):
        """
        Test reading JSONL with chunksize using direct connector call
        """
        reader = wrangles.connectors.json.read('tests/samples/data.jsonl', chunksize=1)

        chunk_count = 0
        for chunk in reader:
            assert isinstance(chunk, _pd.DataFrame)
            chunk_count += 1
        
        assert chunk_count > 0


class TestBackwardCompatibility:
    """
    Test that json connector works with existing data files
    """
    
    def test_read_existing_json_sample(self):
        """
        Test reading existing sample JSON file
        """
        df = wrangles.connectors.json.read('tests/samples/data.json')
        assert not df.empty
        assert 'Find' in df.columns and 'Replace' in df.columns

    def test_read_existing_jsonl_sample(self):
        """
        Test reading existing sample JSONL file
        """
        df = wrangles.connectors.json.read('tests/samples/data.jsonl')
        assert not df.empty
        assert 'Find' in df.columns and 'Replace' in df.columns

    def test_round_trip_json(self):
        """
        Test writing and reading back JSON produces same data
        """
        filename = f"tests/temp/{_uuid.uuid4()}.json"
        original_df = _pd.DataFrame({
            'col1': ['a', 'b', 'c'],
            'col2': [1, 2, 3],
            'col3': [1.5, 2.5, 3.5]
        })
        
        wrangles.connectors.json.write(original_df, filename)
        result_df = wrangles.connectors.json.read(filename)
        
        assert original_df.columns.tolist() == result_df.columns.tolist()
        assert len(original_df) == len(result_df)
        
        _os.remove(filename)

    def test_round_trip_jsonl(self):
        """
        Test writing and reading back JSONL produces same data
        """
        filename = f"tests/temp/{_uuid.uuid4()}.jsonl"
        original_df = _pd.DataFrame({
            'col1': ['a', 'b', 'c'],
            'col2': [1, 2, 3],
            'col3': [1.5, 2.5, 3.5]
        })
        
        wrangles.connectors.json.write(original_df, filename)
        result_df = wrangles.connectors.json.read(filename)
        
        assert original_df.columns.tolist() == result_df.columns.tolist()
        assert len(original_df) == len(result_df)
        
        _os.remove(filename)


class TestComplexParameterCombinations:
    """
    Complex tests utilizing at least 4 parameters to ensure robust handling
    of parameter combinations in real-world scenarios.
    """
    
    def test_read_jsonl_with_multi_params(self):
        """
        Test reading JSONL with 5 parameters: columns, nrows, encoding, lines, orient
        """
        df = wrangles.connectors.json.read(
            'tests/samples/data.jsonl',
            columns=['Find'],
            nrows=2,
            encoding='utf-8',
            lines=True,
            orient='records'
        )
        assert df.columns.tolist() == ['Find']
        assert len(df) == 2
    
    def test_read_jsonl_chunksize_multi_params(self):
        """
        Test reading JSONL with 5 parameters: chunksize, columns, encoding, lines, precise_float
        """
        reader = wrangles.connectors.json.read(
            'tests/samples/data.jsonl',
            chunksize=1,
            columns=['Replace'],
            encoding='utf-8',
            lines=True,
            precise_float=True
        )
        
        chunks = list(reader)
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.columns.tolist() == ['Replace']
            assert len(chunk) <= 1
    
    def test_read_json_dtype_and_dates(self):
        """
        Test reading JSON with 5 parameters: columns, dtype, convert_dates, keep_default_dates, encoding
        Complex scenario with type conversion and date handling
        """
        filename = f"tests/temp/{_uuid.uuid4()}.json"
        
        # Create test data with mixed types
        test_df = _pd.DataFrame({
            'string_col': ['a', 'b', 'c'],
            'int_col': [1, 2, 3],
            'float_col': [1.1, 2.2, 3.3],
            'date_col': ['2023-01-01', '2023-01-02', '2023-01-03']
        })
        wrangles.connectors.json.write(test_df, filename)
        
        # Read with multiple parameters
        df = wrangles.connectors.json.read(
            filename,
            columns=['string_col', 'int_col', 'float_col', 'date_col'],
            dtype={'string_col': str, 'int_col': int},
            convert_dates=['date_col'],
            keep_default_dates=False,
            encoding='utf-8'
        )
        
        assert len(df) == 3
        assert df.columns.tolist() == ['string_col', 'int_col', 'float_col', 'date_col']
        
        _os.remove(filename)
    
    def test_read_compressed_jsonl_multi_params(self):
        """
        Test reading compressed JSONL with 5 parameters: compression, nrows, lines, columns, encoding
        """
        filename = f"tests/temp/{_uuid.uuid4()}.jsonl.gz"
        
        # Create compressed test file
        test_df = _pd.DataFrame({
            'col1': [f'value_{i}' for i in range(10)],
            'col2': list(range(10)),
            'col3': [i * 1.5 for i in range(10)]
        })
        wrangles.connectors.json.write(test_df, filename)
        
        # Read with multiple parameters
        df = wrangles.connectors.json.read(
            filename,
            compression='gzip',
            nrows=5,
            lines=True,
            columns=['col1', 'col2'],
            encoding='utf-8'
        )
        
        assert len(df) == 5
        assert df.columns.tolist() == ['col1', 'col2']
        assert 'col3' not in df.columns
        
        _os.remove(filename)
    
    def test_write_json_formatting_params(self):
        """
        Test writing JSON with 5 parameters: orient, indent, index, compression, columns
        Complex formatting scenario
        """
        filename = f"tests/temp/{_uuid.uuid4()}.json"
        
        df = _pd.DataFrame({
            'col1': ['a', 'b', 'c'],
            'col2': [1, 2, 3],
            'col3': [1.5, 2.5, 3.5],
            'col4': ['ignore', 'ignore', 'ignore']
        })
        
        wrangles.connectors.json.write(
            df,
            filename,
            orient='records',
            indent=4,
            index=False,
            compression='infer',
            columns=['col1', 'col2', 'col3']
        )
        
        # Verify file was created with proper formatting
        with open(filename, 'r') as f:
            content = f.read()
        assert '    ' in content  # Check for 4-space indentation
        
        # Verify data integrity
        result_df = wrangles.connectors.json.read(filename)
        assert result_df.columns.tolist() == ['col1', 'col2', 'col3']
        assert 'col4' not in result_df.columns
        assert len(result_df) == 3
        
        _os.remove(filename)
    
    def test_write_jsonl_with_date_params(self):
        """
        Test writing JSONL with 5 parameters: date_format, date_unit, lines, columns, encoding
        Complex scenario with date handling
        """
        filename = f"tests/temp/{_uuid.uuid4()}.jsonl"
        
        df = _pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie'],
            'timestamp': _pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']),
            'value': [100, 200, 300],
            'extra': ['drop', 'drop', 'drop']
        })
        
        wrangles.connectors.json.write(
            df,
            filename,
            date_format='iso',
            date_unit='s',
            lines=True,
            columns=['name', 'timestamp', 'value'],
            index=False
        )
        
        # Verify the file was written correctly
        result_df = wrangles.connectors.json.read(filename)
        assert result_df.columns.tolist() == ['name', 'timestamp', 'value']
        assert len(result_df) == 3
        assert 'extra' not in result_df.columns
        
        _os.remove(filename)
    
    def test_write_json_precision_params(self):
        """
        Test writing JSON with 5 parameters: double_precision, force_ascii, orient, index, columns
        Complex scenario with precision and encoding
        """
        filename = f"tests/temp/{_uuid.uuid4()}.json"
        
        df = _pd.DataFrame({
            'id': [1, 2, 3],
            'precise_value': [1.123456789012345, 2.987654321098765, 3.456789012345678],
            'text': ['test', 'data', 'here'],
            'unicode': ['café', 'naïve', 'résumé'],
            'extra': ['x', 'y', 'z']
        })
        
        wrangles.connectors.json.write(
            df,
            filename,
            double_precision=15,
            force_ascii=False,
            orient='records',
            index=False,
            columns=['id', 'precise_value', 'text', 'unicode']
        )
        
        # Verify data integrity
        result_df = wrangles.connectors.json.read(filename)
        assert len(result_df) == 3
        assert result_df.columns.tolist() == ['id', 'precise_value', 'text', 'unicode']
        assert 'extra' not in result_df.columns
        
        _os.remove(filename)
    
    def test_write_compressed_jsonl_multi_params(self):
        """
        Test writing compressed JSONL with 6 parameters: compression, lines, orient, index, date_format, columns
        """
        filename = f"tests/temp/{_uuid.uuid4()}.jsonl.gz"
        
        df = _pd.DataFrame({
            'product': ['Widget A', 'Widget B', 'Widget C'],
            'price': [19.99, 29.99, 39.99],
            'created': _pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']),
            'category': ['electronics', 'electronics', 'home'],
            'internal_id': [1001, 1002, 1003]
        })
        
        wrangles.connectors.json.write(
            df,
            filename,
            compression='gzip',
            lines=True,
            orient='records',
            index=False,
            date_format='epoch',
            columns=['product', 'price', 'created', 'category']
        )
        
        # Verify compressed file was created and is readable
        assert _os.path.exists(filename)
        result_df = wrangles.connectors.json.read(filename)
        assert len(result_df) == 3
        assert result_df.columns.tolist() == ['product', 'price', 'created', 'category']
        assert 'internal_id' not in result_df.columns
        
        _os.remove(filename)
    
    def test_round_trip_complex_params(self):
        """
        Test round-trip with complex parameters on both write and read
        Parameters: columns, orient, indent, encoding (write) + columns, encoding, dtype (read)
        """
        filename = f"tests/temp/{_uuid.uuid4()}.json"
        
        original_df = _pd.DataFrame({
            'string_field': ['alpha', 'beta', 'gamma'],
            'integer_field': [10, 20, 30],
            'float_field': [1.11, 2.22, 3.33],
            'boolean_field': [True, False, True],
            'drop_field': ['x', 'y', 'z']
        })
        
        # Write with complex parameters
        wrangles.connectors.json.write(
            original_df,
            filename,
            columns=['string_field', 'integer_field', 'float_field', 'boolean_field'],
            orient='records',
            indent=2,
            index=False
        )
        
        # Read with complex parameters
        result_df = wrangles.connectors.json.read(
            filename,
            columns=['string_field', 'integer_field', 'float_field'],
            encoding='utf-8',
            dtype={'string_field': str, 'integer_field': int}
        )
        
        assert len(result_df) == 3
        assert result_df.columns.tolist() == ['string_field', 'integer_field', 'float_field']
        assert 'boolean_field' not in result_df.columns
        assert 'drop_field' not in result_df.columns
        
        _os.remove(filename)
    
    def test_chunksize_with_complex_params(self):
        """
        Test chunked reading with 6 parameters: chunksize, nrows, columns, encoding, lines, precise_float
        """
        filename = f"tests/temp/{_uuid.uuid4()}.jsonl"
        
        # Create larger test file
        large_df = _pd.DataFrame({
            'id': list(range(100)),
            'value': [i * 2.5 for i in range(100)],
            'category': [f'cat_{i % 5}' for i in range(100)],
            'description': [f'item_{i}' for i in range(100)]
        })
        wrangles.connectors.json.write(large_df, filename)
        
        # Read in chunks with multiple parameters
        reader = wrangles.connectors.json.read(
            filename,
            chunksize=10,
            nrows=50,  # Only read first 50 rows
            columns=['id', 'value', 'category'],
            encoding='utf-8',
            lines=True,
            precise_float=True
        )
        
        chunks = list(reader)
        total_rows = sum(len(chunk) for chunk in chunks)
        
        assert total_rows == 50  # Should respect nrows
        assert len(chunks) == 5  # 50 rows / 10 per chunk
        
        for chunk in chunks:
            assert chunk.columns.tolist() == ['id', 'value', 'category']
            assert 'description' not in chunk.columns
        
        _os.remove(filename)
    
    def test_recipe_with_complex_read_params(self):
        """
        Test using recipe format with complex read parameters
        Parameters: columns, encoding, lines, nrows
        """
        recipe = """
          read:
            - json:
                name: tests/samples/data.jsonl
                columns:
                  - Find
                encoding: utf-8
                lines: true
                nrows: 2
          wrangles:
            - convert.case:
                input: Find
                case: upper
        """
        df = wrangles.recipe.run(recipe)
        assert df.columns.tolist() == ['Find']
        assert len(df) == 2
    
    def test_recipe_with_complex_write_params(self):
        """
        Test using recipe format with complex write parameters
        Parameters: columns, orient, indent, index
        """
        filename = f"tests/temp/{_uuid.uuid4()}.json"
        recipe = f"""
          read:
            - test:
                rows: 5
                values:
                  col1: value1
                  col2: value2
                  col3: value3
          write:
            - json:
                name: {filename}
                columns:
                  - col1
                  - col2
                orient: records
                indent: 2
                index: false
        """
        wrangles.recipe.run(recipe)
        
        # Verify output
        result_df = wrangles.connectors.json.read(filename)
        assert result_df.columns.tolist() == ['col1', 'col2']
        assert len(result_df) == 5
        
        _os.remove(filename)