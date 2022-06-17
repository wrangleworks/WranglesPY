import pandas as _pd
import pymongo
import logging as _logging

_schema = {}

def read(user: str, password: str, database: str, collection: str, cluster: str, query: dict, projection: dict = {}) -> _pd.DataFrame:
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
    
    _logging.info(f": Importing Data :: {cluster}")
    
    conn = f"mongodb+srv://{user}:{password}@{cluster}/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(conn)
    db = client[database]
    col = db[collection]
    
    result = []
    for x in col.find(query, projection):
        result.append(x)
    
    df = _pd.DataFrame(result)        
    return df

_schema['read'] = """


"""
