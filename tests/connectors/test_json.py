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