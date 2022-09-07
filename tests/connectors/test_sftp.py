from wrangles.connectors.sftp import read, write
import pandas as pd
import io


# temp file in bytes
data = pd.DataFrame({
    'col': ['test1', 'test2']
})

normal_df = data
data = data.to_csv(index=False).encode('utf-8')

# Read class
class read_test():
    def get(file, local):
        return data

# Reading file from SFTP
def test_read_sftp(mocker):
    m = mocker.patch("fabric.Connection")
    m.return_value = read_test
    m2 = mocker.patch("wrangles.connectors.file.read")
    m2.return_value = normal_df
    config = {
        'host': 'wrangles',
        'user': 'mario',
        'password': '1234',
        'file': 'test.csv',
        'port': 22
    }
    df = read(**config)
    assert df.equals(normal_df)


# write temp
class write_test():
    def put(tempFile, remote):
        return None

# Writing
def test_write_sftp(mocker):
    m = mocker.patch("wrangles.connectors.file.write")
    m.return_value = None
    m2 = mocker.patch("fabric.Connection")
    m2.return_value = write_test
    config = {
        'df': normal_df,
        'host': 'wrangles',
        'user': 'mario',
        'password': '1234',
        'file': 'test.csv',
        'port': 22,
    }
    assert write(**config) == None