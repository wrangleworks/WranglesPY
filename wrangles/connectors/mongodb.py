import pandas as _pd
import pymongo
import logging as _logging

_schema = {}

def read(user: str, password: str, database: str, collection: str, host: str, query: dict, projection: dict = {}) -> _pd.DataFrame:
    """
    Import data from a MongoDB database
    
    >>> from wrangles.connectors import mongodb
    >>> df = mongodb.read(user='user, password='password', database='db', cluster='cluster0.mongodb.net', query='{"name": "Fey"}',projection='{"_id": 0, "name": 1, "position": 1}')
    
    :param user: User with access to the database
    :param password: Password of user
    :param database: Database to be queried
    :param collection: Collection to be queried
    :param cluster: cluster-url
    :param query: mongoDB query
    :param projection: (Optional) Select which fields to include
    """
    
    _logging.info(f": Importing Data :: {database}.{collection}")
    
    conn = f"mongodb+srv://{user}:{password}@{host}/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(conn)
    db = client[database]
    col = db[collection]
    
    result = []
    for x in col.find(query, projection):
        result.append(x)
    
    df = _pd.DataFrame(result)        
    return df

_schema['read'] = """
type: object
description: Import data from a mongoDB Server
required:
  - user
  - password
  - database
  - collection
  - host
  - query
properties:
  user:
    type: string
    description:  User with access to the database
  password:
    type: string
    description: Password of user
  database:
    type: string
    description: Database to be queried
  host:
    type: string
    description: cluster-url
  query:
    type: string
    description: mongoDB query
  projection:
    type: string
    description: Select which fields to include
"""
