import logging as _logging
from io import BytesIO as _BytesIO
from typing import Union as _Union
import pandas as _pd
import requests as _requests
from . import file as _file


_schema = {}


def _get_packages_in_dataset(host, dataset, api_key):
    response = _requests.get(
        url = f"{host}/api/3/action/package_show?id={dataset}",
        headers={'Authorization': api_key}
    )
    
    if response.status_code == 403:
        raise RuntimeError("Access Denied to the CKAN Server. If this is a private resource, you must provide an API_KEY.")
    
    if response.status_code != 200:
        raise ValueError("Unable to find dataset on CKAN server. Check host and dataset name.")
    
    results = {}
    for resource in response.json()["result"]["resources"]:
        results[resource["name"]] = resource
    
    return results


def read(host: str, dataset: str, file: str, api_key: str = None, **kwargs) -> _pd.DataFrame:
    """
    Read data from CKAN
    
    :param host: The host name of the CKAN site. e.g. https://data.example.com
    :param dataset: The name of the dataset. This should be the url version e.g. my-dataset
    :param file: The name of the specific file within the dataset.
    :param api_key: API Key for the CKAN site.
    :param kwargs: (Optional) Named arguments to pass to respective pandas read a file function.
    """
    _logging.info(f": Importing Data :: {host}/{dataset}/{file}")
    
    packages = _get_packages_in_dataset(host, dataset, api_key)

    if file not in packages.keys():
        raise ValueError('File not found in dataset')
    
    # Download the requested data
    response = _requests.get(packages[file]["url"], headers={'Authorization': api_key})
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
    description: The host name of the CKAN site. e.g. https://data.example.com
  dataset:
    type: string
    description: The name of the dataset. This should be the url version e.g. my-dataset
  file:
    type: string
    description: The name of the specific file within the dataset. e.g. example.csv
  api_key:
    type: string
    description: API Key for the CKAN site.
"""

def write(df: _pd.DataFrame, host: str, dataset: str, file: str, api_key: str, **kwargs):
    """
    Write a file to a dataset in CKAN
    
    :param df: Dataframe to be exported
    :param host: The host name of the CKAN site. e.g. https://data.example.com
    :param dataset: The name of the dataset. This should be the url version e.g. my-dataset
    :param file: The name of the specific file within the dataset. e.g. example.csv
    :param api_key: API Key for the CKAN site.
    :param kwargs: (Optional) Named arguments to pass to respective pandas write a file function.
    """
    memory_file = _BytesIO()
    _file.write(df, name=file, file_object=memory_file, **kwargs)
    
    _logging.info(f": Writing File :: {host} / {dataset} / {file}")

    packages = _get_packages_in_dataset(host, dataset, api_key)

    if file in packages.keys():
        response = _requests.post(
            url = f"{host}/api/action/resource_update",
            data = {"id": packages[file]["id"]},
            headers = {"Authorization": api_key},
            files = {'upload': (file, memory_file.getvalue())}
        )
    else:
        response = _requests.post(
            url = f"{host}/api/action/resource_create",
            data={
                "package_id": dataset,
                "name": file
            },
            headers={"Authorization": api_key},
            files={'upload': (file, memory_file.getvalue())}
        )

    if response.status_code == 403:
        raise RuntimeError("Access Denied to the CKAN Server. Check your API_KEY.")
    elif response.status_code != 200:
        raise RuntimeError("Upload to CKAN Failed")
    
_schema['write'] = """
type: object
description: Write a file to a dataset in CKAN
required:
  - host
  - api_key
  - dataset
  - file
properties:
  host:
    type: string
    description: The host name of the CKAN site. e.g. https://data.example.com
  api_key:
    type: string
    description: API Key for the CKAN site.
  dataset:
    type: string
    description: The name of the dataset. This should be the url version e.g. my-dataset
  file:
    type: string
    description: The name of the specific file within the dataset. e.g. example.csv
"""

class download:
    """
    Download files from CKAN to the local file system
    """
    _schema = {
        "run": """
          type: object
          description: Download data from CKAN and save to the local file system
          required:
            - host
            - dataset
            - file
          properties:
            host:
              type: string
              description: The host name of the CKAN site. e.g. https://data.example.com
            dataset:
              type: string
              description: The name of the dataset. This should be the url version e.g. my-dataset
            file:
              type:
                - string
                - array
              description: A name or list of files within the dataset. e.g. example.csv
            api_key:
              type: string
              description: API Key for the CKAN site.
            output_file:
              type:
                - string
                - array
              description: |
                A name or list of names that the output will be saved as.
                If omitted, defaults to the same as the file.
          """
    }

    def run(
        host: str,
        dataset: str,
        file: _Union[str, list],
        api_key: str = None,
        output_file: _Union[str, list] = None
    ) -> None:
        """
        Download data from CKAN and save to the local file system
        
        :param host: The host name of the CKAN site. e.g. https://data.example.com
        :param dataset: The name of the dataset. This should be the url version e.g. my-dataset
        :param file: The name of the specific file within the dataset.
        :param api_key: API Key for the CKAN site.
        :param output_file: A name or list of names that the output will be saved as. If omitted, defaults to the same as the file.
        """
        _logging.info(f": Downloading data from CKAN :: {host} / {dataset} / {file}")
        
        if not output_file: output_file = file

        if not isinstance(file, list): file = [file]
        if not isinstance(output_file, list): output_file = [output_file]
        
        packages = _get_packages_in_dataset(host, dataset, api_key)
        
        for fname, output_fname in zip(file, output_file):
            if fname not in packages.keys():
                raise ValueError(f'File {fname} not found in dataset')
            
            # Download the requested data
            response = _requests.get(packages[fname]["url"], headers={'Authorization': api_key})

            with open(output_fname, "wb") as f:
                f.write(_BytesIO(response.content).getbuffer())


class upload:
    """
    Upload a file or list of files to a CKAN dataset
    """
    _schema = {
        "run": """
            type: object
            description: Upload a file or list of files to a CKAN dataset
            required:
              - host
              - api_key
              - dataset
              - file
            properties:
              host:
                type: string
                description: The host name of the CKAN site. e.g. https://data.example.com
              api_key:
                type: string
                description: API Key for the CKAN site.
              dataset:
                type: string
                description: The name of the dataset. This should be the url version e.g. my-dataset
              file:
                type:
                  - string
                  - array
                description: The name of the specific file within the dataset. e.g. example.csv
              output_file:
                type:
                  - string
                  - array
                description: |
                  A name or list of names that the files will be saved as.
                  If omitted, defaults to the original filename.
        """
    }

    def run(
        host: str,
        dataset: str,
        api_key: str,
        file: _Union[str, list],
        output_file: _Union[str, list] = None
    ) -> None:
        """
        Upload a file or list of files to a CKAN dataset
        
        :param host: The host name of the CKAN site. e.g. https://data.example.com
        :param dataset: The name of the dataset. This should be the url version e.g. my-dataset
        :param api_key: API Key for the CKAN site.
        :param file: A name or list of names of files to be uploaded. e.g. example.csv
        :param output_file: A name or list of names that the files will be saved as. If omitted, defaults to the original filename.
        """
        _logging.info(f": Uploading data to CKAN :: {host} / {dataset} / {file}")

        packages = _get_packages_in_dataset(host, dataset, api_key)

        if not output_file: output_file = file

        if not isinstance(file, list): file = [file]
        if not isinstance(output_file, list): output_file = [output_file]

        for fname, output_fname in zip(file, output_file):
            with open(fname, "rb") as f:
                memory_file = _BytesIO(f.read())

            if output_fname in packages.keys():
                response = _requests.post(
                    url = f"{host}/api/action/resource_update",
                    data = {"id": packages[output_fname]["id"]},
                    headers = {"Authorization": api_key},
                    files = {'upload': (output_fname, memory_file.getvalue())}
                )
            else:
                response = _requests.post(
                    url = f"{host}/api/action/resource_create",
                    data={
                        "package_id": dataset,
                        "name": output_fname
                    },
                    headers={"Authorization": api_key},
                    files={'upload': (output_fname, memory_file.getvalue())}
                )

            if response.status_code == 403:
                raise RuntimeError("Access Denied to the CKAN Server. Check your API_KEY.")
            elif response.status_code != 200:
                raise RuntimeError(f"Upload to CKAN Failed - {fname}")
