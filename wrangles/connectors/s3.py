import pandas as _pd
import boto3 as _boto3
import logging as _logging
from . import file as _file
from io import BytesIO as _BytesIO

_schema = {}

def read(bucket: str, key: str, access_key: str = None, secret_access_key: str = None, **kwargs) -> _pd.DataFrame:
    """
    Import a data from a file in AWS S3
    
    :param bucket: The name of the bucket to download object from
    :param key: The name of the key to download from
    :param access_key: S3 access key
    :param secret_access_key: S3 secret access key
    """
    
    _logging.info(f": Importing Data :: {bucket}.{key}")
    
    # Check if access keys are not none then auth
    if None not in (access_key, secret_access_key):
        s3 = _boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)
    else:
        # if using environment variables
        s3 = _boto3.client('s3')
      
    response = s3.get_object(Bucket=bucket, Key=key)['Body']
    response = _BytesIO(response.read())
    df = _file.read(key, file_object=response, **kwargs)    
 
    return df
    
_schema['read'] = """
type: object
description: Import a data from a file in AWS S3
required:
  - bucket
  - key
properties:
  bucket:
    type: string
    description: The name of the bucket where file will be read
  key:
    type: string
    description: The name of the key to download from
  access_key:
    type: string
    description: S3 access key
  secret_access_key:
    type: string
    description: S3 secret access key
    
"""

def write(df: _pd.DataFrame, bucket: str, key: str, access_key: str = None, secret_access_key: str = None, **kwargs):
    """
    Write a file in AWS S3
    
    :param df: Dataframe to be exported
    :param bucket: The name of the bucket where file will be written
    :param key: The name of the key to download from
    :param access_key: S3 access key
    :param secret_access_key: S3 secret access key
    """
  
  # Check if access keys are not none then auth
    if None not in (access_key, secret_access_key):
        s3 = _boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)
    else:
    # if using environment variables
        s3 = _boto3.client('s3')
        
    memory_file = _BytesIO()
    _file.write(df, name=key, file_object=memory_file, **kwargs)
    memory_file.seek(0, 0)
    _logging.info(f": Writing File :: {bucket}.{key}")
    s3.put_object(Bucket=bucket, Body=memory_file, Key=key)
    
_schema['write'] = """
type: object
description: write files to AWS S3
required:
  - bucket
  - key
properties:
  bucket:
    type: string
    description: The name of the bucket where file will be written
  key:
    type: string
    description: The name of the key of the file written
  access_key:
    type: string
    description: S3 access key
  secret_access_key:
    type: string
    description: S3 secret access key
"""
    
  
  