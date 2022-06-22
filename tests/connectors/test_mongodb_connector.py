import wrangles
import pymongo
import pandas as pd

class temp_col():
    def find(query, projection):
        return {'name': 'Data1'}
    
        

from wrangles.connectors.mongodb import read, write

# return an empty query
def test_read(mocker):
    m2 = mocker.patch("pymongo.MongoClient")
    m2.return_value = {"db": {"col": temp_col}}
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