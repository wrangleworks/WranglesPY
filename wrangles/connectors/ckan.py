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