import logging as _logging
from io import BytesIO as _BytesIO
import pandas as _pd
import requests as _requests
from . import file as _file


_schema = {}

def read(host: str, dataset: str, file: str, api_key: str = None, **kwargs) -> _pd.DataFrame:
    """
    Read data from CKAN
    
    :param host: The host name of the CKAN site. e.g. data.example.com
    :param dataset: The name of the dataset. This should be the url version e.g. my-dataset
    :param file: The name of the specific file within the dataset.
    :param api_key: API Key for the CKAN site.
    :param kwargs: (Optional) Named arguments to pass to respective pandas read a file function.
    """
    _logging.info(f": Importing Data :: {host}/{dataset}/{file}")
    
    response = _requests.get(
        url = f"{host}/api/3/action/package_show?id={dataset}",
        headers={'Authorization': api_key}
    )
    
    # Get download url from dataset and file names
    download_url = None
    for resource in response.json()["result"]["resources"]:
        if resource["name"] == file:
            download_url = resource["url"]

    if download_url == None:
        raise ValueError('Dataset Not Found')

    # Download the requested data
    response = _requests.get(download_url, headers={'Authorization': api_key})
    file_io = _BytesIO(response.content)
    df = _file.read(file, file_object=file_io, **kwargs)    
 
    return df
    
_schema['read'] = """
type: object
description: Read data from CKAN
required:
  - host
  - dataset
  - file
properties:
  host:
    type: string
    description: The host name of the CKAN site. e.g. data.example.com
  dataset:
    type: string
    description: The name of the dataset. This should be the url version e.g. my-dataset
  file:
    type: string
    description: The name of the specific file within the dataset.
  api_key:
    type: string
    description: API Key for the CKAN site.
"""

def write(df: _pd.DataFrame, host: str, dataset: str, file: str, api_key: str = None, **kwargs):
    """
    Write a file in AWS S3
    
    :param df: Dataframe to be exported
    :param bucket: The name of the bucket where file will be written
    :param key: The name of the key to download from
    :param access_key: S3 access key
    :param secret_access_key: S3 secret access key
    :param kwargs: (Optional) Named arguments to pass to respective pandas write a file function.
    """      
    memory_file = _BytesIO()
    _file.write(df, name=file, file_object=memory_file, **kwargs)
    memory_file.seek(0, 0)
    _logging.info(f": Writing File :: {host} / {dataset} / {file}")

    response = _requests.post(
        url = f"{host}/api/action/resource_create",
        data={
            "package_id": dataset,
            "name": file
        },
        headers={"Authorization": api_key},
        files=[('upload', memory_file.read())]
    )
    print()
    
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