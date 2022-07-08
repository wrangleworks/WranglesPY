import wrangles
import pymongo
import pandas as pd
import enum

class Subscriptable:
    def __class_getitem__(cls, item):
        return cls._get_child_dict()[item]
    @classmethod
    def _get_child_dict(cls):
        return {k: v for k, v in cls.__dict__.items() if not k.startswith('_')}

# Reading a file
class client_mock_read(Subscriptable):
    def list_database_names():
        return ['db']
    class db_class(Subscriptable):
        def list_collection_names():
            return ['col']
        class col_class(Subscriptable):
            def find(query, projection):
                return {'name': 'Data1'}
        col = col_class
    db = db_class
    
        
from wrangles.connectors.mongodb import read, write

# return an empty query
def test_read(mocker):
    m1 = mocker.patch("pymongo.MongoClient")
    m1.return_value = client_mock_read
    config = {
        'user': 'us',
        'password': 'pass',
        'database': 'db',
        'collection': 'col',
        'host': 'host',
        'query': '{"name": "Data1"}',
        'projection': '{}'
    }
    test = read(**config)
    assert test[0][0] == 'name'
    
    
df = pd.DataFrame({
    'name': ['Data1']
})

# Writing a file
class client_mock_write(Subscriptable):
    def list_database_names():
        return ['db']
    class db_class(Subscriptable):
        def list_collection_names():
            return ['col']
        class col_class(Subscriptable):
            def insert_many(df):
                return 'Items inserted'
        col = col_class
    db = db_class

def test_write(mocker):
    m1 = mocker.patch("pymongo.MongoClient")
    m1.return_value = client_mock_write
    config = {
        'df': df,
        'user': 'us',
        'password': 'pass',
        'database': 'db',
        'collection': 'col',
        'host': 'host',
        'action': 'INSERT',
    }
    test = write(**config)
    assert test == None