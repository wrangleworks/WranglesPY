import pandas as _pd
import pymongo as _pymongo
import logging as _logging
from typing import Union as _Union

_schema = {}

def read(user: str, password: str, database: str, collection: str, host: str, query: dict = {}, projection: dict = {}) -> _pd.DataFrame:
    """
    Import data from a MongoDB database
    
    >>> from wrangles.connectors import mongodb
    >>> df = mongodb.read(user='user, password='password', database='db', host='cluster0.mongodb.net', query='{"name": "Fey"}',projection='{"_id": 0, "name": 1, "position": 1}')
    
    :param user: User with access to the database
    :param password: Password of user
    :param database: Database to be queried
    :param collection: Collection to be queried
    :param host: mongoDB cluster-url
    :param query: mongoDB query
    :param projection: (Optional) Select which fields to include
    """
    
    _logging.info(f": Importing Data :: {database}.{collection}")
    
    conn = f"mongodb+srv://{user}:{password}@{host}/?retryWrites=true&w=majority"
    client = _pymongo.MongoClient(conn)
    db = client[database]
    col = db[collection]
    
    result = []
    for x in col.find(query, projection):
        result.append(x)
    
    df = _pd.DataFrame(result)
    
    try:
      client.close()
    except:
      pass
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
    description: mongoDB cluster-url
  query:
    type: string
    description: mongoDB query
  projection:
    type: string
    description: Select which fields to include
"""

_schema = {}

def write(df: _pd.DataFrame, user: str, password: str, database: str, collection: str, host: str, action: str, query: dict = None, update: dict=None, columns: _Union[str, list] = None) -> None:
    """
    Write data into a monfoDB database
    
    >>> from wrangles.connectors import mongodb
    >>> df = mongodb.write(user='user, password='password', database='db', host='cluster0.mongodb.net', action: INSERT, data = [{"name": "Mario"}, {"name": "Luigi"}])
    
    :param df: Dataframe to be exported
    :param user: User with access to the database
    :param password: Password of user
    :param database: Database to be queried
    :param collection: Collection to be queried
    :param host: mongobd cluster-url
    :param action: actions supported INSERT, UPDATE
    :pram query: mongoDB query to search for value to update or delete, only valid when using UPDATE, DELETE
    :param update: mongoDB query value to update, only valid when using UPDATE
    
    """
    conn = f"mongodb+srv://{user}:{password}@{host}/?retryWrites=true&w=majority"
    client = _pymongo.MongoClient(conn)
    db = client[database]
    col = db[collection]
    
    # Select only specific columns if user requests them
    if columns is not None: df = df[columns]
    
    if action.upper() == 'INSERT':
        col.insert_many(df.to_dict(orient='records'))
    elif action.upper() == 'UPDATE':
        col.update_many(query, update)
    
    client.close()
_schema['write'] = """
type: object
description: insert, delete, or update data to a mongoDB Server
required:
  - user
  - password
  - database
  - collection
  - host
  - action
properties:
  user:
    type: string
    description: User with access to the database
  password:
    type: string
    description: Password of user
  database:
    type: string
    description: Database to be queried
  host:
    type: string
    description: mongoDB cluster-url
  action:
    type: string
    description: action to perform, actions supported INSERT UPDATE
  query:
    type: object
    description: mongoDB query to search for value to update or delete, only valid when using UPDATE, DELETE
  update:
    type: object
    description: mongoDB query value to update, only valid when using UPDATE
"""

