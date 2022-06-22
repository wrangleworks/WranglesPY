import wrangles
import pymongo
import pandas as pd

# from wrangles.connectors.mongodb import read, write
# def test_read(mocker):
#     m2 = mocker.patch("pymongo.MongoClient")
#     m2.return_value = {"db": {"col": "collection"}}
#     data = [{'name': 'Data1'}, {'name': 'Data2'}]
#     m = mocker.patch("pymongo.collection.Collection.find")
#     m.return_value = data
#     config = {
#         'user': 'us',
#         'password': 'pass',
#         'database': 'db',
#         'collection': 'col',
#         'host': 'host',
#         'query': '{"name": "Data1"}',
#         'projection': '{}'
#     }
#     test = read(**config)
#     print()