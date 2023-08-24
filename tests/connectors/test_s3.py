import pandas as pd
import os
import wrangles
import pytest
import time

from wrangles.connectors.s3 import read, write

s3_key = os.getenv('AWS_ACCESS_KEY_ID', '...')
s3_secret = os.getenv('AWS_SECRET_ACCESS_KEY', '...')

# Reading a file in S3
def test_read_1():
    recipe = f"""
    read:
      - s3:
          bucket: wrwx-public
          key: World Cup Winners.xlsx
          access_key: {s3_key}
          secret_access_key: {s3_secret}
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0]['Winners'] == 'Uruguay'
    
# using environment variables
def test_read_2():
    recipe = f"""
    read:
      - s3:
          bucket: wrwx-public
          key: World Cup Winners.xlsx
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0]['Winners'] == 'Uruguay'



# Writing to an S3 file
def test_write_1():
    recipe = f"""
    write:
      - s3:
          bucket: wrwx-public
          key: World Cup Titles.xlsx
          access_key: {s3_key}
          secret_access_key: {s3_secret}
    """
    data = pd.DataFrame({
        'Country': ['Brazil', 'Germany', 'Italy'],
        'Titles': [5, 4, 4,],
    })
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Country'] == 'Brazil'

# Writing using environment variables
def test_write_2():
    recipe = f"""
    write:
      - s3:
          bucket: wrwx-public
          key: World Cup Titles.xlsx
    """
    data = pd.DataFrame({
        'Country': ['Brazil', 'Germany', 'Italy'],
        'Titles': [5, 4, 4,],
    })
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Country'] == 'Brazil'
    
    

def test_file_upload_and_download_1():
    """
    Upload file to s3 key and file not included
    """
    recipe = f"""
    run:
      on_start:
        - s3.upload_files:
           bucket: wrwx-public
           file: tests/samples/data.csv
           aws_access_key_id: {s3_key}
           aws_secret_access_key: {s3_secret}
    """
    wrangles.recipe.run(recipe)
    time.sleep(3)
    # Reading uploaded file to complete the cycle
    recipe2 = f"""
    run:
      on_start:
        - s3.download_files:
            bucket: wrwx-public
            key: data.csv
            file: tests/temp/data.csv
            aws_access_key_id: {s3_key}
            aws_secret_access_key: {s3_secret}
    read:
      - file:
          name: tests/temp/data.csv
    """
    
    df = wrangles.recipe.run(recipe2)
    assert df.iloc[0]['Find'] == 'BRG'
    
# Key and file included
def test_file_upload_and_download_2():
    recipe = f"""
    run:
      on_start:
        - s3.upload_files:
           bucket: wrwx-public
           key: Test_Upload_File.csv
           file: tests/samples/data.csv
           aws_access_key_id: {s3_key}
           aws_secret_access_key: {s3_secret}
    """
    wrangles.recipe.run(recipe)
    time.sleep(3)
    # Reading uploaded file to complete the cycle
    recipe2 = f"""
    run:
      on_start:
        - s3.download_files:
            bucket: wrwx-public
            key: Test_Upload_File.csv
            file: tests/temp/temp_download_data.csv
            aws_access_key_id: {s3_key}
            aws_secret_access_key: {s3_secret}
    read:
      - file:
          name: tests/temp/temp_download_data.csv
    """
    
    df = wrangles.recipe.run(recipe2)
    assert df.iloc[0]['Find'] == 'BRG'
    
    
# Downloading multiple files error
def test_download_error():
    recipe = """
    run:
      on_success:
        - s3.download_files:
            bucket: wrwx-public
            key:
              - Test_Upload_File.csv
              - World Cup Titles.csv
            file:
              - tests/temp/temp_download_data.csv
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe)
    assert info.typename == 'ValueError' and info.value.args[0] == 's3.download_files: An equal number of keys and files must be provided'

def test_upload_error():
    recipe = """
    run:
      on_start:
        - s3.upload_files:
           bucket: wrwx-public
           file:
             - tests/samples/data.csv
             - tests/samples/data.json
           key:
             - Test_Upload_File.csv
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe)
    assert info.typename == 'ValueError' and info.value.args[0] == 's3.upload_files: An equal number of files and keys must be provided'
