import logging as _logging
from io import BytesIO as _BytesIO
from typing import Union as _Union
import pandas as _pd
from . import file as _file
from ..utils import LazyLoader as _LazyLoader

# Lazy load external dependency
_boto3 = _LazyLoader('boto3')

_schema = {}

def read(
    bucket: str,
    key: str,
    access_key: str = None,
    secret_access_key: str = None,
    **kwargs
) -> _pd.DataFrame:
    """
    Import data from a file in AWS S3
    
    :param bucket: The name of the bucket to download object from
    :param key: The name of the key to download from
    :param access_key: S3 access key
    :param secret_access_key: S3 secret access key
    :param kwargs: (Optional) Named arguments to pass to respective pandas read a file function.
    """
    _logging.info(f": Reading data from S3 :: {bucket} / {key}")

    # Check if access keys are not none then auth
    if None not in (access_key, secret_access_key):
        s3 = _boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)
    else:
        # if using environment variables
        s3 = _boto3.client('s3')
    
    try:
        response = s3.get_object(Bucket=bucket, Key=key)['Body']
    except s3.exceptions.NoSuchKey:
        raise FileNotFoundError(f"File not found in S3 bucket :: {bucket} / {key}")
    except s3.exceptions.NoSuchBucket:
        raise RuntimeError(f"S3 bucket does not exist :: {bucket} / {key}")
    except s3.exceptions.ClientError as e:
        raise RuntimeError(f"Failed to read file from S3 :: {e.response.get('Error', {}).get('Message', '')} :: {bucket} / {key}")
    except:
        raise RuntimeError(f"Failed to read file from S3 :: {bucket} / {key}")

    response = _BytesIO(response.read())
    df = _file.read(key, file_object=response, **kwargs)    
 
    return df
    
_schema['read'] = """
type: object
description: Import data from a file in AWS S3
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
    Write a file to AWS S3
    
    :param df: Dataframe to be exported
    :param bucket: The name of the bucket where file will be written
    :param key: The name of the key to download from
    :param access_key: S3 access key
    :param secret_access_key: S3 secret access key
    :param kwargs: (Optional) Named arguments to pass to respective pandas write a file function.
    """
    _logging.info(f": Writing data to S3 :: {bucket} / {key}")

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

    try:
        s3.put_object(Bucket=bucket, Body=memory_file, Key=key)
    except s3.exceptions.NoSuchBucket:
        raise RuntimeError(f"S3 bucket does not exist :: {bucket} / {key}")
    except s3.exceptions.ClientError as e:
        raise RuntimeError(f"Failed to write file to S3 :: {e.response.get('Error', {}).get('Message', '')} :: {bucket} / {key}")
    except:
        raise RuntimeError(f"Failed to write file to S3 :: {bucket} / {key}")


_schema['write'] = """
type: object
description: Write a file to AWS S3
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

class download_files:
    """
    Download file(s) from S3 and save to the local file system.
    """
    _schema = {
        "run": """
            type: object
            description: Download file(s) from S3 and save to the local file system.
            required:
                - bucket
                - key
            properties:
                bucket:
                    type: string
                    description: S3 Bucket
                key:
                    type:
                      - string
                      - array
                    description: S3 file key or list of keys to download
                file:
                    type:
                      - string
                      - array
                    description: Local filename or list of filenames to save the downloaded files as
                endpoint_url:
                    type: string
                    description: Override the S3 host for alternative S3 storage providers.
                aws_access_key_id:
                    type: string
                    description: Set the access key. Can also be set as an environment variable
                aws_secret_access_key:
                    type: string
                    description: Set the access secret. Can also be set as an environment variable
        """
    }

    def run(bucket: str, key: _Union[str, list], file: _Union[str, list] = None, **kwargs):
        """
        Download file(s) from S3 and save to the local file system.

        :param bucket: S3 Bucket
        :param key: S3 file key or list of keys to download
        :param file: Local filename or list of filenames to save the downloaded files as.
        :param endpoint_url: Override the S3 host for alternative S3 storage providers.
        :param aws_access_key_id: Set the access key. Can also be set as an environment variable
        :param aws_secret_access_key: Set the access secret. Can also be set as an environment variable
        """
        _logging.info(f": Downloading files from S3 :: {bucket} / {key}")

        s3 = _boto3.client('s3', **kwargs)

        if isinstance(key, str): key = [key]

        # If a list of filename isn't provided, then save
        # in the current directory as the key's filename
        if not file:
            file = [k.split('/')[-1] for k in key]

        if isinstance(file, str):
            file = [file]

        if len(file) != len(key):
            raise ValueError('s3.download_files: An equal number of keys and files must be provided')

        for f, k in zip(file, key):
            try:
                s3.download_file(bucket, k, f)
            except s3.exceptions.ClientError as e:
                if e.response.get('Error', {}).get('Code') == "404":
                    raise FileNotFoundError(f"File not found :: {bucket} / {k}")
                elif e.response.get('Error', {}).get('Code') == "403":
                    raise PermissionError(f"Permission denied to download file :: {bucket} / {k}")
                else:
                    raise RuntimeError(f"Failed to download file from S3 :: {e.response.get('Error', {}).get('Message', '')} :: {bucket} / {k}")
            except:
                raise RuntimeError(f"Failed to download file from S3 :: {bucket} / {k}")

class upload_files:
    """
    Upload file(s) to S3 from the local file system.
    """
    _schema = {
        "run": """
            type: object
            description: Upload file(s) to S3 from the local file system.
            required:
                - bucket
                - file
            properties:
                bucket:
                    type: string
                    description: S3 Bucket
                key:
                    type:
                      - string
                      - array
                    description: S3 file key or list of keys to upload as
                file:
                    type:
                      - string
                      - array
                    description: File or list of files to upload.
                endpoint_url:
                    type: string
                    description: Override the S3 host for alternative S3 storage providers.
                aws_access_key_id:
                    type: string
                    description: Set the access key. Can also be set as an environment variable
                aws_secret_access_key:
                    type: string
                    description: Set the access secret. Can also be set as an environment variable
        """
    }

    def run(bucket: str, file: _Union[str, list], key: _Union[str, list] = None, **kwargs):
        """
        Upload file(s) to S3 from the local file system.

        :param bucket: S3 Bucket
        :param file: File or list of files to upload.
        :param key: S3 file key or list of keys to upload as
        :param endpoint_url: Override the S3 host for alternative S3 storage providers.
        :param aws_access_key_id: Set the access key. Can also be set as an environment variable
        :param aws_secret_access_key: Set the access secret. Can also be set as an environment variable
        """
        _logging.info(f": Uploading files to S3 :: {bucket} / {key}")

        s3 = _boto3.client('s3', **kwargs)

        if isinstance(file, str): file = [file]

        # If a list of filename isn't provided, then save
        # in the current directory as the key's filename
        if not key:
            key = [k.split('/')[-1] for k in file]

        if isinstance(key, str):
            key = [key]

        if len(file) != len(key):
            raise ValueError('s3.upload_files: An equal number of files and keys must be provided')

        for f, k in zip(file, key):
            try:
                s3.upload_file(f, bucket, k)
            except:
                raise RuntimeError(f"Failed to write file to S3 :: {bucket} / {k}")
