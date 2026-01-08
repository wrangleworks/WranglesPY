import logging as _logging
from io import BytesIO as _BytesIO
from typing import Union as _Union
import pandas as _pd
from . import file as _file
from ..utils import LazyLoader as _LazyLoader
import os as _os

# Lazy load external dependency
_boto3 = _LazyLoader('boto3')

_schema = {}

def read(
    bucket: str,
    file_key: str = None,
    access_key: str = None,
    secret_access_key: str = None,
    **kwargs
) -> _pd.DataFrame:
    """
    Import data from a file in AWS S3
    
    :param bucket: The name of the bucket to download object from
    :param file_key: The name of the key to download from. Use this parameter instead of the 'key'.
    :param access_key: S3 access key
    :param secret_access_key: S3 secret access key
    :param kwargs: (Optional) Named arguments to pass to respective pandas read a file function.
    """
    # Backwards compatibility: accept deprecated 'key' via kwargs
    compat_key = kwargs.pop('key', None)
    if file_key is None and compat_key is not None:
        file_key = compat_key

    if file_key is None:  
        raise ValueError("file_key must be provided")  

    _logging.info(f": Reading data from S3 :: {bucket} / {file_key}")

    # Check if access keys are not none then auth
    if None not in (access_key, secret_access_key):
        s3 = _boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)
    else:
        # if using environment variables
        s3 = _boto3.client('s3')
    
    try:  
        response = s3.get_object(Bucket=bucket, Key=file_key)['Body']  
    except s3.exceptions.NoSuchKey:  
        raise FileNotFoundError(f"File not found in S3 bucket :: {bucket} / {file_key}")  
    except s3.exceptions.NoSuchBucket:  
        raise RuntimeError(f"S3 bucket does not exist :: {bucket} / {file_key}")  
    except s3.exceptions.ClientError as e:  
        # Preserve original AWS error details  
        error_msg = e.response.get('Error', {}).get('Message', str(e))  
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')  
        _logging.error(f"AWS S3 ClientError [{error_code}]: {error_msg}")  
        raise RuntimeError(f"Failed to read file from S3 [{error_code}]: {error_msg} :: {bucket} / {file_key}") from e  
    except Exception as e:  
        _logging.error(f"Unexpected AWS S3 error: {str(e)}")  
        raise RuntimeError(f"Failed to read file from S3: {str(e)} :: {bucket} / {file_key}") from e

    response = _BytesIO(response.read())
    df = _file.read(file_key, file_object=response, **kwargs)    
 
    return df
    
_schema['read'] = """
type: object
description: Import data from a file in AWS S3
required:
  - bucket
properties:
  bucket:
    type: string
    description: The name of the bucket where file will be read
  file_key:
    type: string
        description: The name of the key to download from. Use this parameter instead of the 'key'.
  access_key:
    type: string
    description: S3 access key
  secret_access_key:
    type: string
    description: S3 secret access key
    
"""

def write(df: _pd.DataFrame, bucket: str, file_key: str = None, access_key: str = None, secret_access_key: str = None, **kwargs):
    """
    Write a file to AWS S3
    
    :param df: Dataframe to be exported
    :param bucket: The name of the bucket where file will be written
    :param file_key: The name of the key to download from. Use this parameter instead of the 'key'.
    :param access_key: S3 access key
    :param secret_access_key: S3 secret access key
    :param kwargs: (Optional) Named arguments to pass to respective pandas write a file function.
    """
    # Backwards compatibility: accept deprecated 'key' via kwargs
    compat_key = kwargs.pop('key', None)
    if file_key is None and compat_key is not None:
        file_key = compat_key
    if file_key is None:
        raise ValueError("file_key must be provided")
    
    _logging.info(f": Writing data to S3 :: {bucket} / {file_key}")

    # Check if access keys are not none then auth
    if None not in (access_key, secret_access_key):
        s3 = _boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)
    else:
    # if using environment variables
        s3 = _boto3.client('s3')
        
    memory_file = _BytesIO()
    _file.write(df, name=file_key, file_object=memory_file, **kwargs)
    memory_file.seek(0, 0)
    _logging.info(f": Writing File :: {bucket}.{file_key}")

    try:  
        s3.put_object(Bucket=bucket, Body=memory_file, Key=file_key)  
    except s3.exceptions.NoSuchBucket:  
        raise RuntimeError(f"S3 bucket does not exist :: {bucket} / {file_key}")  
    except s3.exceptions.ClientError as e:  
        # Preserve original AWS error details  
        error_msg = e.response.get('Error', {}).get('Message', str(e))  
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')  
        _logging.error(f"AWS S3 ClientError [{error_code}]: {error_msg}")  
        raise RuntimeError(f"Failed to write file to S3 [{error_code}]: {error_msg} :: {bucket} / {file_key}") from e  
    except Exception as e:  
        _logging.error(f"Unexpected AWS S3 error: {str(e)}")  
        raise RuntimeError(f"Failed to write file to S3: {str(e)} :: {bucket} / {file_key}") from e


_schema['write'] = """
type: object
description: Write a file to AWS S3
required:
  - bucket
  - file_key
properties:
  bucket:
    type: string
    description: The name of the bucket where file will be written
  file_key:
    type: string
        description: The name of the key of the file written. Use this parameter instead of the 'key'.
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
            properties:
                bucket:
                    type: string
                    description: S3 Bucket
                file_key:
                    type:
                      - string
                      - array
                    description: S3 file key or list of keys to download.
                save_as:
                    type:
                      - string
                      - array
                    description: Local filename or list of filenames to save the downloaded files as (replaces deprecated 'file').
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

    def run(bucket: str, file_key: _Union[str, list] = None, save_as: _Union[str, list] = None, **kwargs):
        """
        Download file(s) from S3 and save to the local file system.

        :param bucket: S3 Bucket
        :param file_key: S3 file key or list of keys to download.
        :param save_as: Local filename or list of filenames to save the downloaded files as.
        :param endpoint_url: Override the S3 host for alternative S3 storage providers.
        :param aws_access_key_id: Set the access key. Can also be set as an environment variable
        :param aws_secret_access_key: Set the access secret. Can also be set as an environment variable
        """
        # Backwards compatibility: accept deprecated 'key' via kwargs
        compat_key = kwargs.pop('key', None)
        if file_key is None and compat_key is not None:
            file_key = compat_key
        # Backwards compatibility: accept deprecated 'file' via kwargs
        compat_file = kwargs.pop('file', None)
        if save_as is None and compat_file is not None:
            save_as = compat_file
        if file_key is None:
            raise ValueError("file_key must be provided")

        _logging.info(f": Downloading files from S3 :: {bucket} / {file_key}")

        s3 = _boto3.client('s3', **kwargs)

        if isinstance(file_key, str): file_key = [file_key]

        # If a list of filename isn't provided, then save
        # in the current directory as the file_key's filename
        if not save_as:
            save_as = [k.split('/')[-1] for k in file_key]

        if isinstance(save_as, str):
            save_as = [save_as]
        if len(save_as) != len(file_key):
            raise ValueError('s3.download_files: An equal number of keys and files must be provided')

        for f, k in zip(save_as, file_key):
            local_dir = _os.path.dirname(f)  
            if local_dir and not _os.path.exists(local_dir):  
                _os.makedirs(local_dir, exist_ok=True)  
                _logging.info(f": Created local directory :: {local_dir}")  
            try:  
                s3.download_file(bucket, k, f)  
            except s3.exceptions.ClientError as e:  
                error_code = e.response.get('Error', {}).get('Code')  
                error_msg = e.response.get('Error', {}).get('Message', str(e))  
                
                if error_code == "404":  
                    _logging.error(f"AWS S3 FileNotFoundError [{error_code}]: {error_msg}")  
                    raise FileNotFoundError(f"File not found [{error_code}]: {error_msg} :: {bucket} / {k}") from e  
                elif error_code == "403":  
                    _logging.error(f"AWS S3 PermissionError [{error_code}]: {error_msg}")  
                    raise PermissionError(f"Permission denied [{error_code}]: {error_msg} :: {bucket} / {k}") from e  
                else:  
                    _logging.error(f"AWS S3 ClientError [{error_code}]: {error_msg}")  
                    raise RuntimeError(f"Failed to download file from S3 [{error_code}]: {error_msg} :: {bucket} / {k}") from e  
            except Exception as e:  
                _logging.error(f"Unexpected AWS S3 download error: {str(e)}")  
                raise RuntimeError(f"Failed to download file from S3: {str(e)} :: {bucket} / {k}") from e

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
            properties:
                bucket:
                    type: string
                    description: S3 Bucket
                file_key:
                    type:
                      - string
                      - array
                    description: S3 file key or list of keys to upload as.
                save_as:
                    type:
                      - string
                      - array
                    description: File or list of files to upload (replaces deprecated 'file').
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

    def run(bucket: str, save_as: _Union[str, list] = None, file_key: _Union[str, list] = None, **kwargs):
        """
        Upload file(s) to S3 from the local file system.

        :param bucket: S3 Bucket
        :param save_as: File or list of files to upload.
        :param file_key: S3 file key or list of keys to upload as.
        :param endpoint_url: Override the S3 host for alternative S3 storage providers.
        :param aws_access_key_id: Set the access key. Can also be set as an environment variable
        :param aws_secret_access_key: Set the access secret. Can also be set as an environment variable
        """
        # Backwards compatibility: accept deprecated 'key' via kwargs
        compat_key = kwargs.pop('key', None)
        if file_key is None and compat_key is not None:
            file_key = compat_key
        # Backwards compatibility: accept deprecated 'file' via kwargs
        compat_file = kwargs.pop('file', None)
        if save_as is None and compat_file is not None:
            save_as = compat_file
        if save_as is None:
            raise ValueError("save_as must be provided")
        
        _logging.info(f": Uploading files to S3 :: {bucket} / {file_key}")

        s3 = _boto3.client('s3', **kwargs)

        if isinstance(save_as, str): save_as = [save_as]

        # If a list of filename isn't provided, then save
        # in the current directory as the file_key's filename
        if not file_key:
            file_key = [k.split('/')[-1] for k in save_as]

        if isinstance(file_key, str):
            file_key = [file_key]

        if len(save_as) != len(file_key):
            raise ValueError('s3.upload_files: An equal number of files and keys must be provided')

        for f, k in zip(save_as, file_key):
            try:  
                s3.upload_file(f, bucket, k)  
            except s3.exceptions.ClientError as e:  
                error_msg = e.response.get('Error', {}).get('Message', str(e))  
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')  
                _logging.error(f"AWS S3 ClientError [{error_code}]: {error_msg}")  
                raise RuntimeError(f"Failed to write file to S3 [{error_code}]: {error_msg} :: {bucket} / {k}") from e  
            except Exception as e:  
                _logging.error(f"Unexpected AWS S3 upload error: {str(e)}")  
                raise RuntimeError(f"Failed to write file to S3: {str(e)} :: {bucket} / {k}") from e
