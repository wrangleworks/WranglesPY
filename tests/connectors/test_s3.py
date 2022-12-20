import pandas as pd
import os
import wrangles

from wrangles.connectors.s3 import read, write

s3_key = os.getenv('S3_KEY_TEST', '...')
s3_secret = os.getenv('S3_SECRET_KEY_TEST', '...')

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
    
# upload file to s3
def test_file_upload():
    recipe = f"""
    run:
      on_start:
        - s3.upload_files:
           bucket: wrwx-public
           file: tests/samples/data.csv
           key: Test_Upload_File.csv
           aws_access_key_id: {s3_key}
           aws_secret_access_key: {s3_secret}

      on_success:
        - s3.download_files:
            bucket: wrwx-public
            key: Test_Upload_File.csv
            aws_access_key_id: {s3_key}
            aws_secret_access_key: {s3_secret}
    """
    wrangles.recipe.run(recipe)
    assert True
