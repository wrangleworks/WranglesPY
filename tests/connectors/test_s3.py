import pandas as pd

from wrangles.connectors.s3 import read, write


# Data 
data = pd.DataFrame({
    'col': ['test1', 'test2']
    })
    
# Dataframe to bytes
data = data.to_csv(index=False).encode('utf-8')

# Classes required to mock test
class resp:
    def read():
        return data

class s3_mock:
    def get_object(Bucket, Key):
        return {'Body': resp}
        

# Reading from a bucket
def test_read_s3(mocker):
    m1 = mocker.patch("boto3.client")
    m1.return_value = s3_mock
    config = {
        'bucket': 'demo-1313',
        'key': 'demo_file.csv',
        'access_key': '123',
        'secret_access_key': '123',
        'encoding': 'ISO-8859-1'
    }
    df = read(**config)
    assert df['col'].iloc[0] == 'test1'
    

# Classes required to mock write test
class s3_mock_write:
    def put_object(Bucket, Body, Key):
        return 'File uploaded!'


# Writing a file
def test_write_s3(mocker):
    m1 = mocker.patch("boto3.client")
    m1.return_value = s3_mock_write
    
    write_data = pd.DataFrame({
        'col': ['test1', 'test2']
    })
    config = {
        'df': write_data,
        'bucket': 'demo-1313',
        'key': 'demo_file.csv',
        'access_key': '123',
        'secret_access_key': '123',
    }
    write(**config) # No response from function

